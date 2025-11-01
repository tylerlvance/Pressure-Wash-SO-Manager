@echo off
:: Batch script to open a cmd window, activate virtual environment, and run main.py
:: Path assumptions:
::   - Project root: C:\Users\tyler\Desktop\FoundersSOManager
::   - Virtual environment: .venv

cd /d "C:\Users\tyler\Desktop\FoundersSOManager"

:: Activate the virtual environment
call .venv\Scripts\activate

:: Run the Python app
python main.py

:: Keep the window open after program exits
pause