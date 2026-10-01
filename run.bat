@echo off
echo Starting RainCheck (Google WeatherNext 3) Streamlit App...
cd /d "%~dp0"
call .venv\Scripts\activate.bat
streamlit run app.py
pause
