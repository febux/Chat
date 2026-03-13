"""
Base application exception class definition.
"""


class BaseAppException(Exception):
    """
    Base application exception class for custom error handling.

    This class extends the built-in Exception class to provide a standardized
    way of handling application-specific exceptions with additional details.

    Attributes:
        error (str, optional): A general description of the error. Defaults to "Unknown error."
    """

    error: str = "Unknown error"

    def __init__(
        self,
        loc: list | None = None,  # Местоположение ошибки, например, ["body", "email"]
        msg: str | None = None,  # Сообщение об ошибке
        error_type: str | None = None,  # Тип ошибки, например, "value_error.missing"
    ):
        self.detail = [{"loc": loc or [], "msg": msg or "Unknown error", "type": error_type or "error"}]
        super().__init__(self.detail)

    def __reduce__(self):
        """
        Reduce the BaseAppException instance for pickling.

        This method is used to provide instructions for pickling the exception object.

        :return: A tuple containing the class and a tuple of arguments for reconstructing the exception.
        """
        return BaseAppException, (self.detail[0]["loc"], self.detail[0]["msg"], self.detail[0]["type"])

    def to_dict(self) -> dict:
        """
        Convert the exception information to a dictionary.

        :return: A dictionary containing the error message and details.
        """
        return {
            "error": self.error,
            "detail": self.detail,
        }
