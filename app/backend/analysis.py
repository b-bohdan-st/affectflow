import sys
import json
import time
import base64
import cv2
import numpy as np
import mediapipe as mp
import subprocess
import threading
import os

sys.stdout.reconfigure(line_buffering=True)

EAR_THRESHOLD = 0.22
MAR_THRESHOLD = 0.65
BLINK_MIN_FRAMES = 2
YAWN_MIN_FRAMES = 15
ATTENTION_SMOOTH = 0.2
FATIGUE_SMOOTH = 0.05
FATIGUE_DECAY = 0.002

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BREAK_PATH = os.path.join(BASE_DIR, "break.py")

def euclidean(a, b):
    return np.linalg.norm(np.array(a) - np.array(b))

def eye_aspect_ratio(eye):
    v1 = euclidean(eye[1], eye[5])
    v2 = euclidean(eye[2], eye[4])
    h = euclidean(eye[0], eye[3])
    return (v1 + v2) / (2.0 * h)

def mouth_aspect_ratio(mouth):
    v = euclidean(mouth[2], mouth[8])
    h = euclidean(mouth[0], mouth[4])
    return v / h

def smooth(prev, new, alpha):
    return prev * (1 - alpha) + new * alpha

def compute_attention(gaze_x, gaze_y, yaw, pitch):
    gaze_dist = np.sqrt(gaze_x**2 + gaze_y**2)
    gaze_score = np.clip(1.0 - gaze_dist * 2.5, 0, 1)
    head_score = np.clip(1.0 - (abs(yaw) / 25 + abs(pitch) / 20), 0, 1)
    return 0.7 * gaze_score + 0.3 * head_score

def fatigue_from_blinks(blink_rate):
    return np.clip(blink_rate / 35.0, 0, 1)

def fatigue_from_eye_closure(eye_closed_frames):
    return np.clip(eye_closed_frames / 20.0, 0, 0.5)

def fatigue_from_yawns(yawns):
    return min(yawns * 0.15, 0.6)

blink_frames = 0
eye_closed_frames = 0
total_blinks = 0
total_yawns = 0
yawn_frames = 0
attention_value = 1.0
fatigue_value = 0.0
break_launched = False

start_time = time.time()

def monitor_break(proc):
    global fatigue_value, break_launched
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        if "break_ended" in line.strip():
            fatigue_value = 0.0
            break_launched = False
            break
    proc.stdout.close()
    proc.wait()
    break_launched = False

mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

for line in sys.stdin:
    if not line.strip():
        continue

    try:
        frame_data = base64.b64decode(line.strip())
        frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
    except:
        continue

    if frame is None:
        continue

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = mp_face_mesh.process(rgb)

    raw_attention = attention_value
    fatigue_delta = 0.0

    if result.multi_face_landmarks:
        lm = result.multi_face_landmarks[0].landmark
        left_eye_idx = [33, 160, 158, 133, 153, 144]
        right_eye_idx = [362, 385, 387, 263, 373, 380]
        left_eye = [(lm[i].x, lm[i].y) for i in left_eye_idx]
        right_eye = [(lm[i].x, lm[i].y) for i in right_eye_idx]

        ear = (eye_aspect_ratio(left_eye) + eye_aspect_ratio(right_eye)) / 2

        if ear < EAR_THRESHOLD:
            blink_frames += 1
            eye_closed_frames += 1
        else:
            if blink_frames >= BLINK_MIN_FRAMES:
                total_blinks += 1
            blink_frames = 0
            eye_closed_frames = 0

        mouth_idx = [61, 291, 81, 13, 311, 308, 402, 14, 178]
        mouth = [(lm[i].x, lm[i].y) for i in mouth_idx]
        mar = mouth_aspect_ratio(mouth)

        if mar > MAR_THRESHOLD:
            yawn_frames += 1
        else:
            if yawn_frames > YAWN_MIN_FRAMES:
                total_yawns += 1
            yawn_frames = 0

        gaze_x = lm[468].x - 0.5
        gaze_y = lm[468].y - 0.5
        yaw = (lm[234].x - lm[454].x) * 100
        pitch = (lm[10].y - lm[152].y) * 100

        raw_attention = compute_attention(gaze_x, gaze_y, yaw, pitch)
        elapsed = time.time() - start_time
        blink_rate = (total_blinks / elapsed) * 60 if elapsed > 1 else 0

        fatigue_delta += fatigue_from_blinks(blink_rate)
        fatigue_delta += fatigue_from_eye_closure(eye_closed_frames)
        fatigue_delta += fatigue_from_yawns(total_yawns)

    attention_value = smooth(attention_value, raw_attention, ATTENTION_SMOOTH)
    fatigue_value += FATIGUE_SMOOTH * fatigue_delta
    fatigue_value -= FATIGUE_DECAY
    fatigue_value = np.clip(fatigue_value, 0, 1)

    if fatigue_value >= 0.6 and not break_launched:
        if os.path.exists(BREAK_PATH):
            break_launched = True
            cmd = ["python", BREAK_PATH] if BREAK_PATH.endswith(".py") else [BREAK_PATH]

            creation_flags = 0
            if os.name == 'nt':
                creation_flags = 0x08000000

            proc = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True, 
                bufsize=1,
                creationflags=creation_flags
            )
            threading.Thread(target=monitor_break, args=(proc,), daemon=True).start()

    print(json.dumps({
        "attention": round(float(attention_value), 3),
        "fatigue": round(float(fatigue_value), 3)
    }))
    sys.stdout.flush()