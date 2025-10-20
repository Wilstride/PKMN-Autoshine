import asyncio

# load_time=3 is timed for NSW2
async def travel_cafe(ctrl, load_time=3):
    # Open map
    await press(ctrl, "plus")
    await asyncio.sleep(0.3)
    # Flick forward for 0.1 s
    await set_left_stick(ctrl, h=0, v=1000)
    await asyncio.sleep(0.05)
    await set_left_stick(ctrl)
    # Wait to snap to fast travel icon
    await asyncio.sleep(0.2)
    # Fly to cafe
    for i in range(5):
        await press(ctrl, "a")
        await asyncio.sleep(0.1)
    # Wait for loading screen
    await asyncio.sleep(load_time)