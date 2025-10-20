import logging
import asyncio
import time
from adapter.joycontrol import JoycontrolAdapter
from adapter.base import Button, Stick

logging.basicConfig(
    level=logging.DEBUG,           # Show DEBUG messages and above
    format='[%(levelname)s] %(name)s: %(message)s'
)

async def _create_adapter():
    adapter = JoycontrolAdapter()
    await adapter.connect()
    return adapter

async def main():
    # Select hunt methodology    
    #hunt_function = cafe_hunt # can be either cafe_hunt(ctrl) or wild_area(ctrl)
    
    # Create and connect controller adapter
    adapter = await _create_adapter()

    # Go to Game
    await adapter.press(Button.HOME)
    await asyncio.sleep(0.5)
    await adapter.press(Button.HOME)
    await asyncio.sleep(0.5)
    # Using normalized inputs in [-1.0..1.0]
    await adapter.stick(Stick.L_STICK, h=0.0, v=1.0) # Up
    print('stick:', adapter.get_stick(Stick.L_STICK), 'cal:', adapter.get_calibration(Stick.L_STICK), 'bytes:', adapter.stick_bytes(Stick.L_STICK))
    await asyncio.sleep(0.5)
    await adapter.stick(Stick.L_STICK, h=1.0, v=0.0) # Right
    print('stick:', adapter.get_stick(Stick.L_STICK), 'cal:', adapter.get_calibration(Stick.L_STICK), 'bytes:', adapter.stick_bytes(Stick.L_STICK))
    await asyncio.sleep(0.5)
    await adapter.stick(Stick.L_STICK, h=0.0, v=-1.0) # Down
    print('stick:', adapter.get_stick(Stick.L_STICK), 'cal:', adapter.get_calibration(Stick.L_STICK), 'bytes:', adapter.stick_bytes(Stick.L_STICK))
    await asyncio.sleep(0.5)
    await adapter.stick(Stick.L_STICK, h=-1.0, v=0.0) # Left
    print('stick:', adapter.get_stick(Stick.L_STICK), 'cal:', adapter.get_calibration(Stick.L_STICK), 'bytes:', adapter.stick_bytes(Stick.L_STICK))
    await asyncio.sleep(5)

    #count = 0
    #start = time.time()
    #while True:
    #    try:
    #        await adapter.press("home")
#
    #        count = count + 1
    #        elapsed = time.time() - start
    #        print(f"Reset {count} after {round(elapsed, 1)} seconds ({round(elapsed/count, 1)} seconds per reset)")
    #    except Exception as e:
    #        logging.warning(f"{e}")
    #        logging.info("Retrying connection in 3s...")
    #        await asyncio.sleep(3)
    #        # wait for the Switch to connect
    #        await adapter.connect()

# run the async main function
asyncio.run(main())
