@echo off
echo Starting Context-Aware Mental Health Assistant...

REM Ensure dependencies are attached to the actual Python launcher
echo Verifying dependencies...
py -m pip install -r requirements.txt >nul 2>&1

REM Create data.json if it doesn't exist
if not exist "data.json" echo {"current_wpm": 0, "backspace_count": 0, "current_emotion": "Neutral", "stress_level_score": 0} > data.json

echo Launching Dashboard...
start cmd /k "py -m streamlit run app.py"

timeout /t 3 /nobreak >nul

echo Launching Sensors...
start cmd /k "py sensors\keyboard_tracker.py"
start cmd /k "py sensors\face_tracker.py"

echo All services launched!
exit
