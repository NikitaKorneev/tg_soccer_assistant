import asyncio
from src.telegram_bot.bot import mainloop


async def main():
    await mainloop()

if __name__ == "__main__":
    asyncio.run(main())
