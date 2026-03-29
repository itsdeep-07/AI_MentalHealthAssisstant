def calculate_stress(data, baseline):
    default_wpm = data.get("current_wpm", 0)
    # The new keyboard sensor doesn't always write backspace count if not pressed, fallback to 0 safely
    backspaces = data.get("backspace_count", 0)
    emotion = data.get("current_emotion", "Neutral")
    
    if not isinstance(emotion, str):
        emotion = "Neutral"
        
    emotion = emotion.lower()
    
    score = 0
    
    # Emotion heuristics
    if emotion in ["angry", "sad", "fear", "disgust"]:
        score += 40
    elif emotion == "neutral":
        score += 10
        
    # Baseline comparison for dynamic thresholding
    if baseline and baseline.get("avg_wpm", 0) > 0:
        avg_wpm = baseline.get("avg_wpm", 0)
        avg_backspaces = baseline.get("avg_backspace_rate", 0)
        
        # If typing significantly faster than baseline (stress indicator)
        if default_wpm > avg_wpm * 1.3:
            score += 25
            
        # If making way more mistakes than baseline
        if backspaces > avg_backspaces * 2 and backspaces > 3:
            score += 35
    else:
        # Fallback to hardcoded thresholds if no baseline is established yet
        if default_wpm > 80:
            score += 20
        if backspaces > 10:
            score += 30
            
    return min(100, score)

def get_stress_level(stress_score):
    if stress_score < 30:
        return "relaxed"
    elif stress_score < 50:
        return "mild"
    elif stress_score < 70:
        return "moderate"
    else:
        return "high"

def get_trigger_type(data, baseline):
    wpm = data.get("current_wpm", 0)
    backspaces = data.get("backspace_count", 0)
    emotion = data.get("current_emotion", "Neutral")
    
    if isinstance(emotion, str):
        emotion = emotion.lower()
    else:
        emotion = "neutral"
    
    triggers = []
    
    if emotion in ["angry", "sad", "fear", "disgust"]:
        triggers.append("facial_expression")
        
    if baseline and baseline.get("avg_wpm", 0) > 0:
        if wpm > baseline["avg_wpm"] * 1.3:
            triggers.append("typing_speed")
        if baseline.get("avg_backspace_rate", 0) > 0 and backspaces > baseline["avg_backspace_rate"] * 2 and backspaces > 3:
            triggers.append("typing_errors")
    else:
        if wpm > 80:
            triggers.append("typing_speed")
        if backspaces > 10:
            triggers.append("typing_errors")
            
    if len(triggers) > 1:
        return "multiple"
    elif len(triggers) == 1:
        return triggers[0]
    else:
        return "unknown"
