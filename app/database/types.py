from __future__ import annotations

import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator


class UUIDType(TypeDecorator):
    """
    Native PostgreSQL UUID type.

    Python:
        uuid.UUID

    Database:
        UUID
    """

    impl = UUID

    cache_ok = True

    def process_bind_param(self, value, dialect):

        if value is None:
            return None

        if isinstance(value, uuid.UUID):
            return value

        return uuid.UUID(str(value))

    def process_result_value(self, value, dialect):

        return value
