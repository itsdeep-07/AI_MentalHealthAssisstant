import sys
import os
import pytest

# Add the project root to the python path so it can import stress_engine
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from stress_engine import calculate_stress, get_stress_level, get_trigger_type

def test_calculate_stress_no_baseline():
    data = {"current_wpm": 90, "backspace_count": 12, "current_emotion": "Angry"}
    score = calculate_stress(data, None)
    # Emotion Angry (40) + WPM > 80 (20) + backspaces > 10 (30) = 90
    assert score == 90

    data_calm = {"current_wpm": 50, "backspace_count": 2, "current_emotion": "Neutral"}
    assert calculate_stress(data_calm, None) == 10  # Only neutral emotion base weight

def test_calculate_stress_with_baseline():
    data = {"current_wpm": 140, "backspace_count": 5, "current_emotion": "Neutral"}
    baseline = {"avg_wpm": 100, "avg_backspace_rate": 1}
    
    score = calculate_stress(data, baseline)
    # Emotion Neutral (10) + WPM > 100*1.3 (25) + backspaces > 1*2 and >3 (35) = 70
    assert score == 70

def test_get_stress_level():
    assert get_stress_level(10) == "relaxed"
    assert get_stress_level(40) == "mild"
    assert get_stress_level(60) == "moderate"
    assert get_stress_level(85) == "high"

def test_get_trigger_type_multiple():
    data = {"current_wpm": 150, "backspace_count": 15, "current_emotion": "Angry"}
    baseline = {"avg_wpm": 100, "avg_backspace_rate": 1}
    assert get_trigger_type(data, baseline) == "multiple"

def test_get_trigger_type_single():
    data = {"current_wpm": 100, "backspace_count": 0, "current_emotion": "Sad"}
    baseline = {"avg_wpm": 100, "avg_backspace_rate": 1}
    assert get_trigger_type(data, baseline) == "facial_expression"