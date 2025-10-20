import asyncio

async def open_game(ctrl):
    # Close controller pairing menu
    await press(ctrl, "a")
    await asyncio.sleep(1)
    # Go to home menu
    await press(ctrl, "home")
    await asyncio.sleep(1)
    # Return to game
    await press(ctrl, "home")
    await asyncio.sleep(0.7)