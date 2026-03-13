"""
JSON formatter for the log records.
"""

import json

from src.backend.common.complex_serializer import ComplexEncoder


def serialize(record, app_name: str | None = None) -> str:
    """
    Serializes a log record into a JSON string.

    This function takes a log record dictionary and converts it into a JSON-formatted string.
    It extracts specific fields from the record and includes additional information such as
    exceptions and extra data if available.

    :param record: A dictionary containing the log record information.
                   Expected to have keys such as 'level', 'message', 'name', 'module',
                   'process', and 'time'.
    :param app_name: The name of the application. Defaults to None.

    :return: A JSON-formatted string representation of the serialized log record.
    """
    record_serialized = dict(
        level=record["level"].name,
        message=record["message"],
        label=record["name"],
        module=record["module"],
        pid=record["process"].id,
        pname=record["process"].name,
        timestamp=record["time"].strftime("%Y-%m-%dT%H:%M:%S"),
    )
    if exception := record.get("exception", None) and record["level"].name in ("ERROR", "CRITICAL"):
        record_serialized["exception"] = exception
    if extra := record.get("extra", None):
        record_serialized |= {**extra, "app_name": app_name}
    return json.dumps(record_serialized, cls=ComplexEncoder)


def patch_serialized(record, app_name: str | None = None) -> None:
    """
    Adds a serialized version of the log record to its 'extra' field.

    This function takes a log record, serializes it using the `serialize` function,
    and adds the serialized version to the record's 'extra' field under the key 'serialized'.

    :param record: A dictionary containing the log record information.
                   Expected to have an 'extra' key, which is also a dictionary.
    :param app_name: The name of the application. Defaults to None.
    """
    record["extra"]["serialized"] = serialize(record, app_name=app_name)


def application_name_patch(app_name: str):
    """
    Adds an 'app_name' field to the log record.

    This function takes a log record, adds a new field 'app_name' with the provided value,
    and returns the updated record.

    :param app_name: The name of the application.
    :return: function that patches the serialized log record with the application name.
    """

    def patch_app_name_serialized(record) -> None:
        """
        Adds a serialized version of the log record to its 'extra' field.

        This function takes a log record, serializes it using the `serialize` function,
        and adds the serialized version to the record's 'extra' field under the key 'serialized'.

        :param record: A dictionary containing the log record information.
                       Expected to have an 'extra' key, which is also a dictionary.
        """
        record["extra"]["serialized"] = serialize(record, app_name=app_name)
        record["extra"]["app_name"] = app_name

    return patch_app_name_serialized
