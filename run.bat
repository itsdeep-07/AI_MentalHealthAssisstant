@echo off
echo Starting Mental Health Assistant...
start "Keyboard Tracker" cmd /k py sensors\keyboard_tracker.py
start "Face Tracker" cmd /k py sensors\face_tracker.py
timeout /t 3 /nobreak > nul
py -m streamlit run app.py
exit