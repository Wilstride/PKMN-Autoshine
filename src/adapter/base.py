"""Base adapter interface for Nintendo Switch controller emulation.

This module defines the abstract base classes and enums for implementing
controller adapters that can emulate Nintendo Switch Pro Controller input.
Concrete implementations should inherit from BaseAdapter and implement all
abstract methods.

The module provides:
    - Button enum for all Nintendo Switch Pro Controller buttons
    - Stick enum for analog stick identification  
    - BaseAdapter abstract base class defining the controller interface

Example:
    Implementing a custom adapter::
    
        class MyAdapter(BaseAdapter):
            async def connect(self) -> None:
                # Implementation-specific connection logic
                pass
                
            async def press(self, btn: Button, duration: float = 0.1) -> None:
                # Implementation-specific button press logic
                pass
"""

import abc
from enum import Enum
from typing import Any, Union


class Button(Enum):
    """Nintendo Switch Pro Controller button identifiers.
    
    This enum provides standardized identifiers for all buttons available
    on a Nintendo Switch Pro Controller. Values correspond to the button
    names used by the underlying controller protocols.
    
    Attributes:
        Face buttons: A, B, X, Y
        Shoulder buttons: L, R, ZL, ZR  
        System buttons: PLUS, MINUS, HOME, CAPTURE
        D-pad buttons: DPAD_UP, DPAD_DOWN, DPAD_LEFT, DPAD_RIGHT
        Stick buttons: L_STICK, R_STICK (clickable sticks)
    """

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
    """Analog stick identifiers for Nintendo Switch Pro Controller.
    
    This enum identifies the left and right analog sticks for position
    control methods. Each stick supports full 2D movement with both
    horizontal and vertical axis control.
    
    Attributes:
        L_STICK: Left analog stick
        R_STICK: Right analog stick
    """

    L_STICK = "l_stick"
    R_STICK = "r_stick"


class BaseAdapter(abc.ABC):
    """Abstract base class for Nintendo Switch controller adapters.

    This class defines the interface that all controller adapter implementations
    must provide. Adapters are responsible for connecting to and controlling
    Nintendo Switch controllers or controller emulation devices.
    
    The interface supports:
        - Connection management
        - Button press simulation with configurable duration
        - Analog stick position control with multiple input formats
        - State reset operations (release buttons, center sticks)
    
    Implementations should handle both raw hardware values and normalized
    floating-point inputs for maximum flexibility.
    
    Example:
        Using an adapter::
        
            adapter = SomeAdapter()
            await adapter.connect()
            await adapter.press(Button.A, duration=0.5)
            await adapter.stick(Stick.L_STICK, h=0.5, v=-0.5)
            await adapter.release_all_buttons()
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the adapter with arbitrary arguments.
        
        Args:
            *args: Positional arguments for adapter-specific configuration
            **kwargs: Keyword arguments for adapter-specific configuration
        """
        pass

    @abc.abstractmethod
    async def connect(self) -> None:
        """Establish connection and prepare the controller for input.
        
        This method should establish any necessary connections (USB, Bluetooth,
        network, etc.) and initialize the controller to a ready state for
        receiving commands.
        
        Raises:
            ConnectionError: If the adapter cannot establish a connection
            RuntimeError: If the adapter fails to initialize properly
        """

    @abc.abstractmethod
    async def press(self, btn: Button, duration: float = 0.1) -> None:
        """Press and release a controller button.
        
        Simulates pressing a button for the specified duration. The button
        will be held down for the duration then automatically released.
        
        Args:
            btn: Button to press (Button enum value or compatible string)
            duration: Time to hold the button in seconds (default: 0.1)
            
        Raises:
            ValueError: If btn is not a valid button identifier
            RuntimeError: If the adapter is not connected or ready
        """

    @abc.abstractmethod
    async def stick(
        self, 
        stick: Stick = Stick.L_STICK, 
        h: Union[int, float] = 0x0800, 
        v: Union[int, float] = 0x0800
    ) -> None:
        """Move an analog stick to the specified position.

        Supports both raw 12-bit integer values (0x000 to 0xFFF) and 
        normalized float values (-1.0 to 1.0) for maximum flexibility.
        
        Args:
            stick: Which stick to move (default: left stick)
            h: Horizontal position. Raw int (0x000-0xFFF) or float (-1.0 to 1.0)
               where -1.0 is full left, 0.0 is center, 1.0 is full right
            v: Vertical position. Raw int (0x000-0xFFF) or float (-1.0 to 1.0)  
               where -1.0 is full down, 0.0 is center, 1.0 is full up
               
        Note:
            Default values (0x0800) represent centered position for raw ints.
            Implementations must handle both int and float input formats.
            
        Raises:
            ValueError: If stick is invalid or coordinates are out of range
            RuntimeError: If the adapter is not connected or ready
        """

    @abc.abstractmethod
    async def release_all_buttons(self) -> None:
        """Release all buttons and return controller to neutral state.

        Sets all buttons to their released state and sends the updated
        controller state. This method should be idempotent and safe to
        call even when the controller is not connected.
        
        Raises:
            RuntimeError: If the adapter encounters an error during reset
        """

    @abc.abstractmethod  
    async def center_sticks(self) -> None:
        """Center both analog sticks to neutral position.

        Moves both left and right analog sticks to their center positions
        (0.0, 0.0 in normalized coordinates) and sends the updated state.
        This method should be idempotent and safe to call even when the
        controller is not connected.
        
        Raises:
            RuntimeError: If the adapter encounters an error during reset
        """
