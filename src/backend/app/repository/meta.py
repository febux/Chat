"""
Repository protocol for interacting with the database using SQLAlchemy for concrete model.
"""

import inspect as python_inspector
from abc import ABC
from enum import Enum
from typing import Any, Generic, Literal, Sequence, Tuple, Type, TypeVar

from sqlalchemy import Result, asc, delete, desc, func, inspect, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.backend.core.logger.logger_factory import logger_bind

logger = logger_bind("ORMRepository")


class OrderType(Enum):
    """
    Enum for ordering query results.
    """

    desc = "desc"
    asc = "asc"


_MODEL_TYPE = TypeVar("_MODEL_TYPE")
_QUERY = TypeVar("_QUERY")


class AbstractRepository(ABC, Generic[_MODEL_TYPE]):
    """
    Abstract repository protocol for concrete model.
    """

    _model: Type[_MODEL_TYPE] | None = None

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with the provided session.

        :param session: AsyncSession: The session for interacting with the database.
        """
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """
        Retrieve the session for interacting with the database.

        :return: AsyncSession: The session for interacting with the database.
        """
        if not self._session:
            raise RuntimeError("Session is not set for this repository")
        return self._session

    @property
    def model(self) -> Type[_MODEL_TYPE]:
        """
        Retrieve the model class for this repository.

        :return: Type[_MODEL_TYPE]: The model class for this repository.
        """
        if not self._model:
            raise RuntimeError("Model is not set for this repository")
        return self._model

    async def execute(
        self,
        query: _QUERY,  # type: ignore[type-var]
        *,
        query_plan: Literal["explain", "explain_analyze"] | None = "explain",
        module_name: str | None = None,
    ) -> Result:
        """
        Execute the provided SQLAlchemy query with optional query plan and logging.

        This function executes the given SQLAlchemy query and logs the query plan and execution time.
        If a query plan is specified, it will be executed before the query. The function also logs the
        module name and function name that called it.

        :param query: (_QUERY): The SQLAlchemy query to be executed.
        :param query_plan: (Literal["explain", "explain_analyze"], optional): The query plan to be executed.
            Defaults to "explain".
        :param module_name: (str, optional): The module name to be logged. If not provided, it will be
            automatically determined.

        :return: Result: The result of executing the SQLAlchemy query.
        """
        if not module_name:
            func_name = await self._get_outer_func_name()
            module_name = f"{self.__class__.__name__}.{func_name}"

        match query_plan:
            case "explain":
                await self._explain_compiled_query(query, module_name=module_name)
            case "explain_analyze":
                await self._explain_compiled_query(query, module_name=module_name, analyze=True)
            case _:
                pass
        return await self.session.execute(query)

    @staticmethod
    async def _get_outer_func_name() -> str:
        """
        Retrieve the name of the function that called the current function.

        This function uses Python's built-in `inspect` module to retrieve the name of the function that
        called the current function. It traverses the call stack to find the caller's function name.

        :return: str: The name of the function that called the current function.
        """
        cur_frame = python_inspector.currentframe()
        cal_frame = python_inspector.getouterframes(cur_frame, 2)
        return cal_frame[2].function

    async def _explain_compiled_query(
        self,
        query: _QUERY,  # type: ignore[type-var]
        module_name: str | None = None,
        *,
        analyze: bool = False,
    ):
        """
        Execute an EXPLAIN query on the provided SQLAlchemy query.

        This function compiles the given SQLAlchemy query into a SQL statement and executes it with
        the EXPLAIN command. The function logs the query plan and execution time. If the 'analyze'
        parameter is set to True, the EXPLAIN ANALYZE command will be used instead.

        :param query: (_QUERY): The SQLAlchemy query to be explained.
        :param module_name: (str, optional): The module name to be logged. If not provided, it will be
            automatically determined.
        :param analyze: (bool, optional): If True, the EXPLAIN ANALYZE command will be used. Defaults to False.
        """

        explain_command = "EXPLAIN "
        if analyze:
            explain_command += "ANALYZE "
        sql = query.compile(self.session.bind, compile_kwargs={"literal_binds": True})  # type: ignore[arg-type]
        explained_result = await self.session.execute(text(f"{explain_command}{sql}"))
        explained_result = "\n".join(explained_result.scalars().all())
        logger.debug(f"{module_name or self.__class__.__name__} :: {sql} -> {explained_result}")

    async def _query_filter_model_parameters(
        self,
        query: _QUERY,
        **kwargs,
    ) -> _QUERY:
        """
        Apply filtering based on provided kwargs for actual model.

        :param query: SQLAlchemy query
        :param kwargs: Keyword arguments for filtering
        :return: SQLAlchemy query with applied filters

        """
        for k, v in kwargs.items():
            query = query.filter(getattr(self.model, k) == v)  # type: ignore[arg-type]

        return query

    @staticmethod
    async def _get_order_direction(
        order_field: str,
    ) -> tuple[Any, str] | Any:
        """
        Determine the sorting direction and field name from the given order field.

        This function parses the order field to determine the sorting direction (ascending or descending)
        and the field name to be used for sorting. The order field can be prefixed with '+' for ascending
        or '-' for descending. If no prefix is present, the default sorting direction is ascending.

        Parameters:
        @param order_field (str): The order field string, which may include a prefix for sorting direction.

        Returns:
        - tuple[Any, str] | Any: A tuple containing the sorting direction (asc or desc) and the field name,
         or the original order field if it does not match the expected format.
        """
        sort_field = None
        direction = asc
        first_char: str = order_field[0]

        if first_char == "-":
            sort_field = order_field[1::]
            direction = desc
        elif first_char == "+":
            sort_field = order_field[1::]
        elif first_char.isalnum():
            sort_field = order_field

        return direction, sort_field

    async def _build_query_row_number(
        self,
        *,
        partition_list: tuple[str, ...] | list[str],
        order_list: tuple[str, ...] | list[str],
    ) -> _QUERY:  # type: ignore[type-var]
        """
        Build a subquery to assign row numbers based on partition and order.

        This function is used to create a subquery that assigns
        a row number to each record within a specified partition,
        ordered by the provided fields.
        The row numbers are assigned based on the order specified in the 'order_by' parameter.

        Parameters:
        @param partition_list: (tuple[str, ...] | list[str]): A tuple or list of field names to partition the data by.
          The row numbers will be assigned separately for each unique combination of these fields.
        @param order_list: (tuple[str, ...] | list[str]): A tuple or list of field names to order the data by.
          The row numbers will be assigned based on the order of these fields within each partition.

        @returns:
        - _QUERY: The constructed subquery with row numbers assigned.
        """
        order_by = []
        for order_field in order_list:
            direction, field = await self._get_order_direction(order_field)
            order_by.append(direction(getattr(self.model, field)))
        init_subquery = select(
            self.model.id,  # type: ignore[arg-type]
            func.row_number()
            .over(
                partition_by=[getattr(self.model, partition_field) for partition_field in partition_list],
                order_by=order_by,
            )
            .label("row_number"),
        )
        if created_at_field := getattr(self.model, "created_at"):
            init_subquery = init_subquery.order_by(desc(created_at_field))

        return init_subquery

    async def _build_order(self, order_key, order_type: OrderType):
        """
        Determine the sorting direction and field name from the given order field.

        This function parses the order field to determine the sorting direction (ascending or descending)
        and the field name to be used for sorting. The order field can be prefixed with '+' for ascending
        or '-' for descending. If no prefix is present, the default sorting direction is ascending.

        Parameters:
        @param order_field (str): The order field string, which may include a prefix for sorting direction.

        Returns:
        - tuple[Any, str] | Any: A tuple containing the sorting direction (asc or desc) and the field name,
         or the original order field if it does not match the expected format.
        """
        if order_type == OrderType.desc:
            return desc(getattr(self.model, order_key))
        else:
            return asc(getattr(self.model, order_key))

    async def get_all(self) -> Sequence[_MODEL_TYPE]:
        """
        Retrieve all entities from the repository.

        :return: A sequence of entities.
        """
        query = select(self.model)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, **kwargs) -> _MODEL_TYPE:
        """
        Create a new entity in the repository.

        :param kwargs: The keyword arguments to initialize the entity with.
        :return: The newly created entity.
        """
        entity = self.model(**kwargs)

        self.session.add(entity)
        await self.session.flush([entity])
        await self.session.refresh(entity)
        return entity

    async def delete(self, **kwargs) -> None:
        """
        Delete entities from the repository based on the provided kwargs.

        :param kwargs: The keyword arguments to filter the entities to delete.
        :return: None
        """
        query = delete(self.model).filter_by(**kwargs)
        await self.session.execute(query)

    async def read(self, **kwargs) -> Sequence[_MODEL_TYPE]:
        """
        Retrieve entities from the repository based on the provided kwargs.

        :param kwargs: The keyword arguments to filter the entities to retrieve.
        :return: A sequence of entities.
        """
        result = await self.session.execute(select(self.model).filter_by(**kwargs))
        entities = result.scalars().all()
        return entities

    async def read_one(
        self,
        *,
        allow_none: bool = True,
        **kwargs,
    ) -> _MODEL_TYPE | None:
        """
        Retrieve a single entity from the repository based on the provided kwargs.

        :param allow_none: If True, return None if no matching entity is found.
        :param kwargs: The keyword arguments to filter the entities to retrieve.
        :return: The entity, or None if no matching entity is found.
        """
        result = await self.session.execute(select(self.model).filter_by(**kwargs).limit(1))
        if allow_none:
            return result.scalars().one_or_none()
        else:
            return result.scalars().one()

    async def read_first(
        self,
        order_key,
        order_type: OrderType,
        *,
        allow_none: bool = True,
        **kwargs,
    ) -> _MODEL_TYPE | None:
        """
        Retrieve the first entity from the repository based on the provided kwargs,
        ordered by the specified field and direction.

        :param order_key: The field name to order the entities by.
        :param order_type: The sorting direction (asc or desc).
        :param allow_none: If True, return None if no matching entity is found.
        :param kwargs: The keyword arguments to filter the entities to retrieve.
        :return: The entity, or None if no matching entity is found.
        """
        order_condition = await self._build_order(order_key, order_type)
        result = await self.session.execute(select(self.model).filter_by(**kwargs).order_by(order_condition).limit(1))
        if allow_none:
            return result.scalars().one_or_none()
        else:
            return result.scalars().one()

    async def _paginate(
        self,
        query: _QUERY,
        limit: int | None,
        offset: int | None,
        unique: bool = True,
    ) -> Tuple[_QUERY, Any | None]:
        """
        Paginate the result set using the provided limit and offset.

        If 'unique' is True, the pagination will be performed on distinct rows of the query.
        If 'unique' is False, the pagination will be performed on all rows of the query.

        :param query: The query to paginate.
        :param limit: The maximum number of rows to return.
        :param offset: The number of rows to skip before returning the result set.
        :param unique: Whether to perform unique pagination.
        :return: The paginated query and the total number of rows.
        """
        if unique:
            count_query = select(func.count()).select_from(query.distinct().subquery())  # type: ignore[arg-type]
        else:
            count_query = select(func.count()).select_from(query.subquery())  # type: ignore[arg-type]
        if limit is not None:
            query = query.limit(limit)  # type: ignore[arg-type]
        if offset is not None:
            query = query.offset(offset)  # type: ignore[arg-type]

        count_result = await self.session.execute(count_query)
        return query, count_result.scalar()

    async def _sort(
        self,
        query: _QUERY,
        sort: str | None,
        model: Any | None = None,
    ) -> _QUERY:
        """
        Sort the result set using the provided sort parameter.

        :param query: The query to sort.
        :param sort: The field name to sort the entities by.
        :param model: The model class to use for sorting (optional).
        :return: The sorted query.
        """
        if sort:
            model_field: Any | None = None

            direction, sort_field = await self._get_order_direction(sort)

            model = model or self.model
            for column in inspect(model).c:
                if column.name == sort_field:
                    model_field = getattr(model, column.name)
                    break

            if sort_field is None:
                raise ValueError(f"Invalid sort field: {sort}")

            query = query.order_by(direction(model_field))  # type: ignore[arg-type]

        return query
