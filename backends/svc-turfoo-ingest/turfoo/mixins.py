from collections.abc import Iterator
from typing import Any, Self


class ConnectableMixin:
    """Adds connection lifecycle management for stateful resources"""

    def connect(self) -> Self:
        """Establish connection to resource"""
        raise NotImplementedError

    def disconnect(self) -> None:
        """Close connection and cleanup"""
        raise NotImplementedError

    def __enter__(self) -> Self:
        return self.connect()

    def __exit__(self, *args) -> None:
        self.disconnect()


class HealthCheckableMixin:
    """Adds health check capability"""

    def is_healthy(self) -> bool:
        """Verify resource is accessible and healthy"""
        raise NotImplementedError


class ReadableMixin:
    """Adds read operations"""

    def get(self, key: str) -> Any:
        """Retrieve data by key"""
        raise NotImplementedError


class WritableMixin:
    """Adds write operations"""

    def create(self, key: str, data: Any) -> None:
        """Create new entry"""
        raise NotImplementedError

    def update(self, key: str, data: Any) -> None:
        """Update existing entry"""
        raise NotImplementedError


class DeletableMixin:
    """Adds delete operations"""

    def delete(self, key: str) -> None:
        """Delete entry by key"""
        raise NotImplementedError


class ListableMixin:
    """Adds listing/querying capability"""

    def list(self, prefix: str = "") -> list[str]:
        """List available keys, optionally filtered by prefix"""
        raise NotImplementedError


class FetchableMixin:
    """Adds batch/stream data retrieval"""

    def fetch(self, **params) -> Iterator[Any]:
        """Fetch multiple items with optional parameters"""
        raise NotImplementedError


class StorableMixin:
    """Adds storage operations for binary data"""

    def save(self, key: str, data: bytes) -> None:
        """Save binary data"""
        raise NotImplementedError

    def load(self, key: str) -> bytes:
        """Load binary data"""
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        raise NotImplementedError
