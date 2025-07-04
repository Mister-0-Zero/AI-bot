from fastapi import FastAPI

from app.core.lifespan import lifespan
from app.core.logging_config import setup_logging
from app.routes import setup_routes

# Настройка логирования (до всех импортов, где используется logger)
setup_logging()

# Создание FastAPI-приложения с поддержкой lifespan
api = FastAPI(title="AI Telegram Bot", lifespan=lifespan)

# Подключение маршрутов
setup_routes(api)

# Это переменная ищет Uvicorn при запуске (например, в Railway Procfile)
app_web = api
