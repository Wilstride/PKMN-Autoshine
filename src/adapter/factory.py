"""Adapter factory for automatic adapter selection and fallback.

This module provides a factory pattern for creating Nintendo Switch controller
adapters with automatic detection and graceful fallback. It supports both
Pico W firmware adapters (USB serial) and joycontrol adapters (Bluetooth).

The factory tries Pico W first for better reliability, then falls back to
joycontrol if the Pico is unavailable. Users can also force a specific
adapter type if needed.

Example:
    Automatic adapter selection::
    
        adapter = await create_adapter()
        
    Force specific adapter::
    
        adapter = await create_adapter(preferred='pico')
        adapter = await create_adapter(preferred='joycontrol')
        
    Test adapter availability::
    
        available = get_available_adapters()
        connectivity = await test_adapter_connectivity()

Typical usage:
    The factory handles all connection details and provides a unified interface
    regardless of which underlying adapter technology is used.
"""

import logging
from typing import Optional

from adapter.base import BaseAdapter

logger = logging.getLogger(__name__)


async def create_adapter(preferred: Optional[str] = None, port: Optional[str] = None) -> BaseAdapter:
    """Create an adapter with automatic detection and fallback.
    
    Attempts to create and connect a controller adapter using the specified
    preference or automatic detection. When no preference is given, tries
    Pico W adapter first (more reliable) then falls back to joycontrol.
    
    Args:
        preferred: Preferred adapter type ('pico' or 'joycontrol'). 
                  If None, uses automatic detection with Pico W first.
        port: Specific TTY port for Pico adapter (e.g., '/dev/ttyACM1').
              If None, will auto-detect available ports.
    
    Returns:
        Connected adapter instance ready for controller commands.
        
    Raises:
        RuntimeError: If no adapter can be connected successfully, with
                     detailed troubleshooting information.
                     
    Example:
        Auto-detect adapter::
        
            adapter = await create_adapter()
            
        Force specific type::
        
            pico_adapter = await create_adapter('pico')
            joy_adapter = await create_adapter('joycontrol')
            
        Use specific port::
        
            adapter = await create_adapter('pico', '/dev/ttyACM1')
    """
    if preferred == 'joycontrol':
        # User specifically requested joycontrol
        return await _create_joycontrol_adapter()
    elif preferred == 'pico':
        # User specifically requested pico
        return await _create_pico_adapter(port)
    else:
        # Auto-detect: try Pico first, then joycontrol
        return await _create_adapter_with_fallback(port)


async def _create_adapter_with_fallback(port: Optional[str] = None) -> BaseAdapter:
    """Create adapter with automatic fallback from Pico W to joycontrol.
    
    Args:
        port: Specific TTY port for Pico adapter. If None, will auto-detect.
    
    Returns:
        Connected adapter instance.
        
    Raises:
        RuntimeError: If both adapter types fail to connect.
    """
    # Try Pico W adapter first (generally more reliable)
    try:
        logger.info("Attempting to connect to Pico W firmware...")
        adapter = await _create_pico_adapter(port)
        logger.info("✓ Connected to Pico W firmware via USB serial")
        return adapter
    except Exception as e:
        logger.warning(f"Pico W connection failed: {e}")
        logger.info("Falling back to joycontrol adapter...")
    
    # Fallback to joycontrol adapter
    try:
        logger.info("Attempting to connect via joycontrol (Bluetooth)...")
        adapter = await _create_joycontrol_adapter()
        logger.info("✓ Connected via joycontrol Bluetooth adapter")
        return adapter
    except Exception as e:
        logger.error(f"Joycontrol connection failed: {e}")
        raise RuntimeError(
            "Could not connect to any adapter!\n"
            "Troubleshooting:\n"
            "1. For Pico W: Make sure firmware is flashed and device appears as /dev/ttyACM0\n"
            "2. For joycontrol: Ensure Bluetooth is configured and Switch is in pairing mode"
        )


async def _create_pico_adapter(port: Optional[str] = None) -> BaseAdapter:
    """Create and connect a Pico W adapter.
    
    Args:
        port: Specific TTY port to use. If None, will auto-detect.
    
    Returns:
        Connected Pico adapter instance.
        
    Raises:
        ImportError: If required dependencies are not available
        ConnectionError: If the Pico device cannot be found or connected
        RuntimeError: If adapter initialization fails
    """
    from adapter.pico import PicoAdapter
    adapter = PicoAdapter(port=port)
    await adapter.connect()
    return adapter


async def _create_joycontrol_adapter() -> BaseAdapter:
    """Create and connect a joycontrol Bluetooth adapter.
    
    Returns:
        Connected joycontrol adapter instance.
        
    Raises:
        ImportError: If joycontrol dependencies are not available
        ConnectionError: If Bluetooth pairing fails
        RuntimeError: If adapter initialization fails
    """
    from adapter.joycontrol import JoycontrolAdapter
    adapter = JoycontrolAdapter()
    await adapter.connect()
    return adapter


def get_available_adapters() -> list[str]:
    """Get list of adapter types available on this system.
    
    Checks for required dependencies and returns which adapter types
    can potentially be used. This doesn't guarantee connectivity.
    
    Returns:
        List of available adapter type names ('pico', 'joycontrol').
        
    Example:
        Check available adapters::
        
            available = get_available_adapters()
            if 'pico' in available:
                print("Pico W adapter is available")
            if 'joycontrol' in available:
                print("Joycontrol adapter is available")
    """
    adapters = []
    
    # Check if Pico adapter dependencies are available
    try:
        import serial
        adapters.append('pico')
    except ImportError:
        pass
    
    # Check if joycontrol dependencies are available
    try:
        import joycontrol
        adapters.append('joycontrol')
    except ImportError:
        pass
    
    return adapters


async def test_adapter_connectivity() -> dict[str, bool]:
    """Test actual connectivity for all available adapter types.
    
    Attempts to create and connect each available adapter type to determine
    which ones are actually functional (not just dependency-available).
    
    Returns:
        Dictionary mapping adapter names to connectivity status.
        Keys are adapter names ('pico', 'joycontrol'), values are
        boolean indicating successful connection.
        
    Example:
        Test which adapters work::
        
            connectivity = await test_adapter_connectivity()
            working_adapters = [name for name, working in connectivity.items() if working]
            print(f"Working adapters: {working_adapters}")
            
    Note:
        This function performs actual connection attempts which may be slow
        and could interfere with other applications using the same devices.
    """
    results = {}
    
    # Test Pico adapter connectivity
    try:
        adapter = await _create_pico_adapter()
        if hasattr(adapter, 'close'):
            adapter.close()
        results['pico'] = True
    except Exception:
        results['pico'] = False
    
    # Test joycontrol adapter connectivity
    try:
        adapter = await _create_joycontrol_adapter()
        # Note: joycontrol adapters typically don't have a close method
        results['joycontrol'] = True
    except Exception:
        results['joycontrol'] = False
    
    return results