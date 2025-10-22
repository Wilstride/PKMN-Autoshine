"""Adapter factory for automatic adapter selection and fallback."""

import logging
from typing import Optional
from adapter.base import BaseAdapter

logger = logging.getLogger(__name__)


async def create_adapter(preferred: Optional[str] = None) -> BaseAdapter:
    """Create an adapter with automatic detection and fallback.
    
    Args:
        preferred: Preferred adapter type ('pico' or 'joycontrol'). 
                  If None, tries Pico first, then joycontrol.
    
    Returns:
        Connected adapter instance.
        
    Raises:
        RuntimeError: If no adapter can be connected.
    """
    if preferred == 'joycontrol':
        # User specifically requested joycontrol
        return await _create_joycontrol_adapter()
    elif preferred == 'pico':
        # User specifically requested pico
        return await _create_pico_adapter()
    else:
        # Auto-detect: try Pico first, then joycontrol
        return await _create_adapter_with_fallback()


async def _create_adapter_with_fallback() -> BaseAdapter:
    """Try Pico adapter first, fall back to joycontrol."""
    # Try Pico W adapter first
    try:
        logger.info("Attempting to connect to Pico W firmware...")
        adapter = await _create_pico_adapter()
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


async def _create_pico_adapter() -> BaseAdapter:
    """Create and connect Pico adapter."""
    from adapter.pico import PicoAdapter
    adapter = PicoAdapter()
    await adapter.connect()
    return adapter


async def _create_joycontrol_adapter() -> BaseAdapter:
    """Create and connect joycontrol adapter."""
    from adapter.joycontrol import JoycontrolAdapter
    adapter = JoycontrolAdapter()
    await adapter.connect()
    return adapter


def get_available_adapters() -> list[str]:
    """Get list of available adapter types."""
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
    """Test connectivity for all available adapters.
    
    Returns:
        Dictionary mapping adapter names to connectivity status.
    """
    results = {}
    
    # Test Pico adapter
    try:
        adapter = await _create_pico_adapter()
        adapter.close()
        results['pico'] = True
    except Exception:
        results['pico'] = False
    
    # Test joycontrol adapter  
    try:
        adapter = await _create_joycontrol_adapter()
        # Note: joycontrol doesn't have a close method
        results['joycontrol'] = True
    except Exception:
        results['joycontrol'] = False
    
    return results