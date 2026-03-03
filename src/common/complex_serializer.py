"""Custom JSON encoder that supports datetime, UUID, and bytes."""

import json
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class ComplexEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that supports serialization of datetime, UUID, bytes, and Enum.
    """

    def default(self, obj: Any) -> Any:  # type: ignore[override]
        """
        Serialize objects of datetime, UUID, bytes, and Enum to their corresponding JSON representations.

        :param obj: The object to serialize.
        :return: The serialized object as a JSON string.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, bytes):
            return obj.hex()
        if isinstance(obj, Enum):
            return obj.value
        return json.JSONEncoder.default(self, obj)


def complex_serializer_json_dumps(data: Any) -> str:
    """
    Serialize a data object into a JSON string using the custom JSON encoder.

    :param data: The data object to serialize.
    :return: The serialized JSON string.
    """
    return ComplexEncoder().encode(data)
