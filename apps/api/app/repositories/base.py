from typing import Generic, TypeVar

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository implementing shared persistence helpers."""

    def __init__(self, model: type[T]):
        self._model = model

    def add(self, instance: T) -> None:
        """Persist an instance to the database.

        Concrete repositories will override this method once persistence logic is implemented.
        """
        raise NotImplementedError

    def get(self, *args, **kwargs) -> T | None:
        """Retrieve an instance from the database."""
        raise NotImplementedError
