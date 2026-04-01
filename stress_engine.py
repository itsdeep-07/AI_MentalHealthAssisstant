def calculate_stress(data, baseline, session_minutes=0):
    default_wpm = data.get("current_wpm", 0)
    backspaces = data.get("backspace_count", 0)
    emotion = data.get("current_emotion", "Neutral")
    
    typo_rate = data.get("typo_rate", 0.0)
    frustration_deletes = data.get("frustration_deletes", 0)
    rhythm_variability = data.get("rhythm_variability", 0.0)
    pause_count = data.get("pause_count", 0)
    emotion_duration = data.get("emotion_duration_seconds", 0)

    if not isinstance(emotion, str):
        emotion = "Neutral"
        
    emotion = emotion.lower()
    score = 0
    
    if baseline and baseline.get("avg_wpm", 0) > 0:
        ratio = default_wpm / baseline["avg_wpm"]
        if ratio > 1.3:
            score += 20
        elif ratio > 1.15:
            score += 10
    else:
        if default_wpm > 70:
            score += 20
            
    if baseline and baseline.get("avg_typo_rate", 0) > 0:
        avg_tr = baseline["avg_typo_rate"]
        if typo_rate > avg_tr + 0.05:
            score += 25
        elif typo_rate > avg_tr + 0.02:
            score += 15
        elif typo_rate > avg_tr + 0.04:
            score += 8
    else:
        if typo_rate > 0.10:
            score += 25
        elif typo_rate > 0.05:
            score += 15
        elif typo_rate > 0.08:
            score += 8
            
    if frustration_deletes >= 3:
        score += 20
    elif frustration_deletes >= 1:
        score += 10

    if rhythm_variability > 0.8:
        score += 15
    elif rhythm_variability > 0.4:
        score += 8

    if pause_count > 10:
        score += 10
    elif pause_count > 2:
        score += 5

    if emotion in ["angry", "sad", "fear", "disgust"]:
        if emotion_duration > 60:
            score += 50
        elif emotion_duration > 20:
            score += 30
        else:
            score += 10
    elif emotion == "surprise":
        score += 15
    elif emotion == "neutral":
        score += 5
        
    if session_minutes > 45:
        score = int(score * (1.0 + (session_minutes - 45) / 90))
            
    return min(100, int(score))

def get_stress_level(stress_score):
    if stress_score < 40:
        return "relaxed"
    elif stress_score < 55:
        return "mild"
    elif stress_score < 70:
        return "moderate"
    else:
        return "high"

def get_trigger_type(data, baseline):
    wpm = data.get("current_wpm", 0)
    backspaces = data.get("backspace_count", 0)
    emotion = data.get("current_emotion", "Neutral")
    
    typo_rate = data.get("typo_rate", 0.0)
    frustration_deletes = data.get("frustration_deletes", 0)
    rhythm_variability = data.get("rhythm_variability", 0.0)
    pause_count = data.get("pause_count", 0)
    emotion_duration = data.get("emotion_duration_seconds", 0)

    if isinstance(emotion, str):
        emotion = emotion.lower()
    else:
        emotion = "neutral"
    
    triggers = []
    
    if baseline and baseline.get("avg_wpm", 0) > 0:
        if wpm > baseline["avg_wpm"] * 1.3:
            triggers.append("high_wpm")
    else:
        if wpm > 80:
            triggers.append("high_wpm")
            
    if baseline and baseline.get("avg_typo_rate", 0) > 0:
        if typo_rate > baseline["avg_typo_rate"] + 0.15:
            triggers.append("high_typo_rate")
    else:
        if typo_rate > 0.05:
            triggers.append("high_typo_rate")
            
    if frustration_deletes >= 1:
        triggers.append("frustration_deletes")
        
    if rhythm_variability > 0.4:
        triggers.append("erratic_rhythm")
        
    if pause_count > 2:
        triggers.append("frequent_pauses")

    if emotion in ["angry", "sad", "fear", "disgust"] and emotion_duration > 20:
        triggers.append("negative_emotion")
            
    if len(triggers) > 1:
        return ",".join(triggers)
    elif len(triggers) == 1:
        return triggers[0]
    else:
        return "unknown"
