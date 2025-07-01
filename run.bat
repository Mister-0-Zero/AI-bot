@echo off
uvicorn main:app_web --host 127.0.0.1 --port 8000 --reload
pause