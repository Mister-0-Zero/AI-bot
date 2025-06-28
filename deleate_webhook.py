import asyncio
from app.telegram.bot import app_tg

async def main():
    await app_tg.initialize()
    await app_tg.bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook удалён")

if __name__ == "__main__":
    asyncio.run(main())