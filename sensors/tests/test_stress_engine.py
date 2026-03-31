import sys
import os
import pytest

# Add the project root to the python path so it can import stress_engine
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from stress_engine import calculate_stress, get_stress_level, get_trigger_type

def test_calculate_stress_no_baseline():
    data = {"current_wpm": 90, "typo_rate": 0.30, "current_emotion": "Angry", "emotion_duration_seconds": 30}
    score = calculate_stress(data, None)
    # WPM > 70 (20) + Typo > 0.25 (25) + Angry > 20s (30) = 75
    assert score == 75

    data_calm = {"current_wpm": 50, "typo_rate": 0.05, "current_emotion": "Neutral"}
    assert calculate_stress(data_calm, None) == 5

def test_calculate_stress_with_baseline():
    data = {"current_wpm": 140, "typo_rate": 0.20, "current_emotion": "Surprise"}
    baseline = {"avg_wpm": 100, "avg_typo_rate": 0.05}
    
    score = calculate_stress(data, baseline)
    # WPM > 1.3x (20) + Typo > baseline+15% (25) + Surprise (15) = 60
    assert score == 60

def test_get_stress_level():
    assert get_stress_level(10) == "relaxed"
    assert get_stress_level(45) == "mild"
    assert get_stress_level(60) == "moderate"
    assert get_stress_level(85) == "high"

def test_get_trigger_type_multiple():
    data = {"current_wpm": 150, "typo_rate": 0.3, "current_emotion": "Angry", "emotion_duration_seconds": 30}
    baseline = {"avg_wpm": 100, "avg_typo_rate": 0.05}
    trigger = get_trigger_type(data, baseline)
    assert "high_wpm" in trigger
    assert "high_typo_rate" in trigger
    assert "negative_emotion" in trigger
    assert trigger == "high_wpm,high_typo_rate,negative_emotion"

def test_get_trigger_type_single():
    data = {"current_wpm": 100, "typo_rate": 0.0, "current_emotion": "Sad", "emotion_duration_seconds": 25}
    baseline = {"avg_wpm": 100, "avg_typo_rate": 0.05}
    assert get_trigger_type(data, baseline) == "negative_emotion"
