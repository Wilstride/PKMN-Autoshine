import logging
import asyncio
import time
from joycontrol.protocol import controller_protocol_factory
from joycontrol.server import create_hid_server
from joycontrol.controller import Controller


logging.basicConfig(
    level=logging.DEBUG,           # Show DEBUG messages and above
    format='[%(levelname)s] %(name)s: %(message)s'
)

controller_type = Controller.PRO_CONTROLLER  # or JOYCON_L / JOYCON_R

async def set_button(ctrl, btn, value=True):
    ctrl.button_state.set_button(btn, value)
    await ctrl.send()

async def press(ctrl, btn):
    await set_button(ctrl, btn, True)
    await asyncio.sleep(0.1)
    await set_button(ctrl, btn, False)

async def set_left_stick(ctrl, h=0, v=0):
    ctrl.l_stick_state.set_h(h)
    ctrl.l_stick_state.set_v(v)
    await ctrl.send()

async def wild_area(ctrl):
    # Hold forward
    await set_left_stick(ctrl, h=0, v=4095)
    await asyncio.sleep(1.3)
    await set_left_stick(ctrl)
    ## Enter area
    await press(ctrl, "a")
    await asyncio.sleep(2)
    await press(ctrl, "plus")
    await asyncio.sleep(0.3)
    for i in range(5):
        await press(ctrl, "a")
        await asyncio.sleep(0.1)
    await asyncio.sleep(3)

async def dratini_hunt(ctrl):
    # Open map
    await press(ctrl, "plus")
    await asyncio.sleep(0.3)
    # Flick forward for 0.1 s
    await set_left_stick(ctrl, h=0, v=1000)
    await asyncio.sleep(0.05)
    await set_left_stick(ctrl)
    await asyncio.sleep(0.2)
    # Fly to cafe
    for i in range(5):
        await press(ctrl, "a")
        await asyncio.sleep(0.1)
    await asyncio.sleep(3)

async def main():
    # create protocol factory
    factory = controller_protocol_factory(controller_type)
    # start the emulated controller (awaitable)
    transport, protocol = await create_hid_server(factory)
    # get a reference to the state being emulated
    ctrl = protocol.get_controller_state()
    # wait for the Switch to connect
    await ctrl.connect()

    # Return to game
    await press(ctrl, "a")
    await asyncio.sleep(1)
    await press(ctrl, "home")
    await asyncio.sleep(1)
    await press(ctrl, "home")
    await asyncio.sleep(1)

    count = 0
    start = time.time()
    while True:
        try:
            # Dratini Hunt
            await dratini_hunt(ctrl)

            # Wild Area Hunt
            #await wild_area(ctrl)

            count = count + 1
            elapsed = time.time() - start
            print(f"Reset {count} after {round(elapsed, 1)} seconds ({round(elapsed/count, 1)} seconds per reset)")
        except Exception as e:
            logging.warning(f"{e}")
            logging.info("Retrying connection in 3s...")
            await asyncio.sleep(3)
            # wait for the Switch to connect
            await ctrl.connect()

# run the async main function
asyncio.run(main())
