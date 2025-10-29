import numpy as np

def calculate_rmssd(ibi_values):
    if len(ibi_values) < 2:
        return None
    squared_differences = np.diff(ibi_values) ** 2
    mean_squared_diff = np.mean(squared_differences)
    return np.sqrt(mean_squared_diff)

def calculate_sdnn(ibi_values):
    if len(ibi_values) < 2:
        return None
    return np.std(ibi_values)

def calculate_stress_score(hr, rmssd, sdnn, max_hr=110, max_rmssd=50, max_sdnn=50):
    normalized_hr = min((hr - 45) / (max_hr - 45), 1)
    normalized_rmssd = min((rmssd - 5) / (max_rmssd - 5), 1)
    normalized_sdnn = min(sdnn / max_sdnn, 1)

    stress_from_hr = normalized_hr
    stress_from_rmssd = 1 - normalized_rmssd
    stress_from_sdnn = 1 - normalized_sdnn

    final_stress_score = (stress_from_hr * 0.4 + stress_from_rmssd * 0.3 + stress_from_sdnn * 0.3) * 100

    return final_stress_score

def calculate_sleep_quality(sleep_states, hr_values, activity_levels):
    """
    Calculate sleep quality score based on sleep states, heart rate, and activity.
    Updated for 4 sleep states: 0=WAKE, 1=LIGHT_SLEEP, 2=REM_SLEEP, 3=DEEP_SLEEP
    Returns a score from 0-100 where higher is better sleep quality.
    """
    if not sleep_states or len(sleep_states) == 0:
        return None
    
    sleep_states = np.array(sleep_states)
    hr_values = np.array(hr_values) if hr_values else None
    activity_levels = np.array(activity_levels) if activity_levels else None
    
    # Calculate sleep stage distribution (4 states)
    total_time = len(sleep_states)
    wake_ratio = np.sum(sleep_states == 0) / total_time
    light_sleep_ratio = np.sum(sleep_states == 1) / total_time
    rem_sleep_ratio = np.sum(sleep_states == 2) / total_time     # ✅ REM state
    deep_sleep_ratio = np.sum(sleep_states == 3) / total_time    # ✅ Deep sleep
    
    # Ideal sleep should have:
    # - Deep sleep ratio (15-20% is optimal)
    # - REM sleep ratio (20-25% is optimal) 
    # - Light sleep ratio (45-55% is optimal)
    # - Low wake ratio (less than 5% is optimal)
    
    deep_score = min(deep_sleep_ratio / 0.20, 1.0) * 100  # Optimal at 20%
    rem_score = min(rem_sleep_ratio / 0.25, 1.0) * 100    # ✅ Optimal at 25% 
    light_score = max(0, 1 - abs(light_sleep_ratio - 0.5) * 2) * 100  # Optimal at 50%
    wake_score = max(0, 1 - wake_ratio / 0.05) * 100  # Optimal below 5%
    
    sleep_distribution_score = (deep_score * 0.3 + rem_score * 0.3 + light_score * 0.3 + wake_score * 0.1)
    
    # Heart rate consistency during sleep (lower variation is better)
    hr_score = 50  # Default if no HR data
    if hr_values is not None and len(hr_values) > 0:
        sleep_hr = hr_values[sleep_states > 0]  # HR during sleep only
        if len(sleep_hr) > 0:
            hr_variability = np.std(sleep_hr)
            hr_score = max(0.0, 100.0 - float(hr_variability) * 2)  # Lower variability = higher score
    
    # Activity during sleep (lower is better)
    activity_score = 50  # Default if no activity data
    if activity_levels is not None and len(activity_levels) > 0:
        sleep_activity = activity_levels[sleep_states > 0]  # Activity during sleep only
        if len(sleep_activity) > 0:
            avg_sleep_activity = np.mean(sleep_activity)
            activity_score = max(0.0, 100.0 - float(avg_sleep_activity) * 200)  # Lower activity = higher score
    
    # Combine scores
    final_score = (sleep_distribution_score * 0.5 + hr_score * 0.25 + activity_score * 0.25)
    
    return min(100, max(0, final_score))

def analyze_sleep_transitions(sleep_states):
    """
    Analyze sleep stage transitions to detect sleep fragmentation.
    Returns number of transitions and fragmentation index.
    """
    if not sleep_states or len(sleep_states) < 2:
        return None, None
    
    sleep_states = np.array(sleep_states)
    transitions = np.sum(np.diff(sleep_states) != 0)
    
    # Fragmentation index: transitions per hour of sleep
    # Assuming each state represents 1 minute of data
    sleep_time_hours = len(sleep_states) / 60.0
    fragmentation_index = transitions / sleep_time_hours if sleep_time_hours > 0 else 0
    
    return transitions, fragmentation_index

def detect_sleep_onset(sleep_states, window_size=10):
    """
    Detect sleep onset time (first sustained period of sleep).
    Returns index of sleep onset or None if not found.
    """
    if not sleep_states or len(sleep_states) < window_size:
        return None
    
    sleep_states = np.array(sleep_states)
    
    for i in range(len(sleep_states) - window_size + 1):
        window = sleep_states[i:i + window_size]
        # Sleep onset: sustained period where most samples are sleep (state > 0)
        if np.sum(window > 0) >= window_size * 0.8:  # 80% of window is sleep
            return i
    
    return None

def detect_wake_periods(sleep_states, min_duration=5):
    """
    Detect periods of wakefulness during the night.
    Returns list of (start_index, duration) tuples.
    """
    if not sleep_states:
        return []
    
    sleep_states = np.array(sleep_states)
    wake_periods = []
    
    i = 0
    while i < len(sleep_states):
        if sleep_states[i] == 0:  # Wake state
            start = i
            while i < len(sleep_states) and sleep_states[i] == 0:
                i += 1
            duration = i - start
            
            if duration >= min_duration:
                wake_periods.append((start, duration))
        else:
            i += 1
    
    return wake_periods