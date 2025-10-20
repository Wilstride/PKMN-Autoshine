import abc
from typing import Any


class BaseAdapter(abc.ABC):
    """Abstract adapter defining the interface for controller adapters.

    Implementations should provide async methods for connect, press, and
    stick so higher-level scripts can use them interchangeably.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    @abc.abstractmethod
    async def connect(self) -> None:
        """Ensure the controller/transport is connected and ready."""

    @abc.abstractmethod
    async def press(self, btn: str, duration: float = 0.1) -> None:
        """Press a button for `duration` seconds."""

    @abc.abstractmethod
    async def stick(self, h: int = 0, v: int = 0) -> None:
        """Move the left stick to horizontal `h` and vertical `v` and send the state."""
