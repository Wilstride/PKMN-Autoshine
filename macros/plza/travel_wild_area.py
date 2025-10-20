import asyncio

# load_time=3 is timed for NSW2
async def wild_area(ctrl, load_time=3):
    # Hold forward
    await set_left_stick(ctrl, h=0, v=4095)
    await asyncio.sleep(1.3)
    await set_left_stick(ctrl)
    # Enter wild area
    await press(ctrl, "a")
    await asyncio.sleep(2)
    # Open map
    await press(ctrl, "plus")
    await asyncio.sleep(0.3)
    # Fly to wild area
    for i in range(5):
        await press(ctrl, "a")
        await asyncio.sleep(0.1)
    # Wait for loading screen
    await asyncio.sleep(load_time)