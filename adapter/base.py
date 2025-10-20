import abc
from typing import Any, Union
from enum import Enum


class Button(Enum):
    """Enum naming for Nintendo Switch Pro controller buttons."""

    A = "a"
    B = "b"
    X = "x"
    Y = "y"
    L = "l"
    R = "r"
    ZL = "zl"
    ZR = "zr"
    PLUS = "plus"
    MINUS = "minus"
    HOME = "home"
    CAPTURE = "capture"
    DPAD_UP = "dpad_up"
    DPAD_DOWN = "dpad_down"
    DPAD_LEFT = "dpad_left"
    DPAD_RIGHT = "dpad_right"
    L_STICK = "l_stick"
    R_STICK = "r_stick"

class Stick(Enum):
    """Enum naming for controller sticks."""

    L_STICK = "l_stick"
    R_STICK = "r_stick"

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
    async def press(self, btn: Button, duration: float = 0.1) -> None:
        """Press a button for `duration` seconds. `btn` may be a `Button` enum or a string."""

    @abc.abstractmethod
    async def stick(self, stick: Stick = Stick.L_STICK, h: int = 0x07FF, v: int = 0x07FF) -> None:
        """Move the chosen stick to horizontal `h` and vertical `v` and send the state."""
