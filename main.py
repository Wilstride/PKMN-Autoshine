import logging
import asyncio
import time
from adapter.joycontrol import JoycontrolAdapter
from adapter.base import Button, Stick
from macros.parser import parse_macro, run_macro

logging.basicConfig(
    level=logging.DEBUG,           # Show DEBUG messages and above
    format='[%(levelname)s] %(name)s: %(message)s'
)

async def _create_adapter():
    adapter = JoycontrolAdapter()
    await adapter.connect()
    return adapter

async def main():
    # Create and connect controller adapter
    adapter = await _create_adapter()

    # Load and run system_open_game macro
    with open('macros/system_open_game.txt') as text:
        commands = parse_macro(text.read())
    await run_macro(adapter, commands)

    # Load and run plza_travel_cafe macro
    with open('macros/plza_travel_cafe.txt') as text:
        commands = parse_macro(text.read())

    print(commands)
    # Repeatedly run the travel cafe macro and log resets
    count = 0
    start = time.time()
    while True:
        await run_macro(adapter, commands)
        count = count + 1
        elapsed = time.time() - start
        print(f"Reset {count} after {round(elapsed, 2)} seconds ({round(elapsed/count, 2)} spr)")

# run the async main function
asyncio.run(main())
