#!/usr/bin/env python3
"""
Web Server for Piper Robotic Arm Control
Two live camera feeds (Orbbec Astra Pro HD + Intel RealSense 455f)
Remote control via web browser from any computer on the network
"""

import os
import sys
import time
import threading
import subprocess
import socket

from flask import Flask, render_template_string, Response, jsonify, request
from flask_socketio import SocketIO
import cv2
import numpy as np

# Add project root for piper_sdk
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from piper_sdk import C_PiperInterface_V2

# ============ Configuration ============
CAN_INTERFACE = "can0"
MOVE_SPD_RATE = 50
CAMERA_1_INDEX = 6   # Orbbec Astra Pro HD (/dev/video6)
CAMERA_2_INDEX = 4   # Intel RealSense 455f RGB (/dev/video4)
SERVER_PORT = 5000

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'piper-web-control'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
robot_state = {
    'connected': False,
    'joints': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    'gripper': 0,
    'speed': 50,
    'status': 'Disconnected'
}

piper = None


# ============ Camera Handler ============
class CameraHandler:
    def __init__(self, name, device_index):
        self.name = name
        self.device_index = device_index
        self.frame = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.cap = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print(f"[OK] {self.name} thread started (device {self.device_index})")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def _capture_loop(self):
        print(f"[..] Opening {self.name} (index {self.device_index})...")

        # Use V4L2 backend explicitly to avoid obsensor backend issues
        self.cap = cv2.VideoCapture(self.device_index, cv2.CAP_V4L2)

        if not self.cap.isOpened():
            print(f"[WARN] {self.name}: V4L2 index {self.device_index} failed, trying path...")
            self.cap = cv2.VideoCapture(f'/dev/video{self.device_index}', cv2.CAP_V4L2)

        if self.cap.isOpened():
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            self.cap.set(cv2.CAP_PROP_FOURCC, fourcc)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            print(f"[OK] {self.name} opened: {w}x{h} @ {fps} FPS")
        else:
            print(f"[ERROR] {self.name}: could not open camera!")

        error_count = 0

        while self.running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self.lock:
                        self.frame = frame.copy()
                    error_count = 0
                else:
                    error_count += 1
                    if error_count > 30:
                        print(f"[WARN] {self.name}: reconnecting...")
                        self.cap.release()
                        time.sleep(1)
                        self.cap = cv2.VideoCapture(self.device_index, cv2.CAP_V4L2)
                        if self.cap.isOpened():
                            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                            self.cap.set(cv2.CAP_PROP_FOURCC, fourcc)
                            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        error_count = 0
            else:
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(placeholder, f"{self.name} Not Available", (120, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                with self.lock:
                    self.frame = placeholder

            time.sleep(0.033)  # ~30 FPS

        if self.cap:
            self.cap.release()
        print(f"[INFO] {self.name} stopped")

    def get_frame(self):
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(placeholder, f"Waiting for {self.name}...", (140, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            return placeholder


# Create two camera handlers
camera1 = CameraHandler("Orbbec Astra", CAMERA_1_INDEX)
camera2 = CameraHandler("RealSense 455f", CAMERA_2_INDEX)


# ============ Robot Functions ============
def check_can_interface():
    try:
        result = subprocess.run(
            ["ip", "link", "show", CAN_INTERFACE],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode != 0:
            return False, "CAN interface not found"
        if "state UP" in result.stdout or "UP" in result.stdout:
            return True, "CAN interface is UP"
        return False, "CAN interface is DOWN"
    except Exception as e:
        return False, str(e)


def get_joints_milli():
    if piper is None:
        return [0, 0, 0, 0, 0, 0]
    js = piper.GetArmJointMsgs().joint_state
    return [js.joint_1, js.joint_2, js.joint_3, js.joint_4, js.joint_5, js.joint_6]


def move_to_joints(joints_milli, speed_rate=None, timeout=8.0):
    if piper is None:
        return False
    if speed_rate is None:
        speed_rate = robot_state['speed']

    start = time.time()
    while time.time() - start < timeout:
        piper.MotionCtrl_2(0x01, 0x01, speed_rate, 0x00)
        piper.JointCtrl(*joints_milli)
        time.sleep(0.02)

        current = get_joints_milli()
        errors = [abs(c - t) for c, t in zip(current, joints_milli)]
        if all(e < 1500 for e in errors):
            return True
    return False


def go_home():
    robot_state['status'] = 'Going home...'
    socketio.emit('log', {'text': 'Moving to home position...', 'type': 'info'})
    success = move_to_joints([0, 0, 0, 0, 0, 0], speed_rate=30)
    robot_state['status'] = 'At home' if success else 'Home timeout'
    return success


# ============ Status Update Thread ============
def status_update_loop():
    while True:
        if piper is not None:
            joints_milli = get_joints_milli()
            robot_state['joints'] = [j / 1000.0 for j in joints_milli]
            robot_state['connected'] = True

        socketio.emit('status_update', robot_state)
        time.sleep(0.2)


# ============ Video Streams ============
def generate_frames(camera):
    while True:
        try:
            frame = camera.get_frame()
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except Exception as e:
            print(f"[WARN] Frame error ({camera.name}): {e}")
        time.sleep(0.05)  # ~20 FPS


# ============ HTML Template ============
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Piper Robot Web Control</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d1117 100%);
            color: #e6edf3;
            min-height: 100vh;
        }
        .header {
            background: rgba(13, 17, 23, 0.95);
            border-bottom: 1px solid #30363d;
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            font-size: 1.4em;
            color: #58a6ff;
        }
        .header .status-badge {
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .status-connected { background: #238636; color: #fff; }
        .status-disconnected { background: #da3633; color: #fff; }
        .main-layout {
            display: grid;
            grid-template-columns: 1fr 380px;
            gap: 16px;
            padding: 16px;
            max-width: 1600px;
            margin: 0 auto;
        }
        .left-col { display: flex; flex-direction: column; gap: 16px; }
        .right-col { display: flex; flex-direction: column; gap: 16px; }
        .cameras-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        .camera-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            overflow: hidden;
        }
        .camera-card .cam-label {
            padding: 8px 14px;
            font-size: 0.85em;
            font-weight: 600;
            color: #8b949e;
            background: rgba(0,0,0,0.3);
            border-bottom: 1px solid #30363d;
        }
        .camera-card img {
            width: 100%;
            height: auto;
            display: block;
            min-height: 240px;
            background: #000;
        }
        .panel {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 16px;
        }
        .panel h2 {
            color: #58a6ff;
            font-size: 1em;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid #21262d;
        }
        /* Joint Display */
        .joints-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 8px;
            margin-bottom: 8px;
        }
        .joint-box {
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 8px;
            text-align: center;
        }
        .joint-box .jlabel { font-size: 0.75em; color: #8b949e; }
        .joint-box .jvalue { font-size: 1.1em; color: #58a6ff; font-weight: bold; font-family: monospace; }
        /* Joint Control Sliders */
        .joint-slider-group {
            margin-bottom: 10px;
        }
        .joint-slider-row {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        }
        .joint-slider-row label {
            width: 30px;
            font-size: 0.85em;
            color: #8b949e;
            font-weight: 600;
        }
        .joint-slider-row input[type="range"] {
            flex: 1;
            height: 6px;
            -webkit-appearance: none;
            background: #30363d;
            border-radius: 3px;
            outline: none;
        }
        .joint-slider-row input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #58a6ff;
            cursor: pointer;
        }
        .joint-slider-row .slider-val {
            width: 55px;
            font-family: monospace;
            font-size: 0.85em;
            text-align: right;
            color: #e6edf3;
        }
        /* Buttons */
        .btn-row {
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 10px 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 600;
            transition: all 0.2s;
            flex: 1;
            min-width: 80px;
        }
        .btn:hover { transform: translateY(-1px); filter: brightness(1.1); }
        .btn:active { transform: translateY(0); }
        .btn-home { background: #238636; color: #fff; }
        .btn-stop { background: #da3633; color: #fff; }
        .btn-send { background: #1f6feb; color: #fff; }
        .btn-gripper-open { background: #2ea043; color: #fff; }
        .btn-gripper-close { background: #e3b341; color: #000; }
        .btn-reset { background: #30363d; color: #e6edf3; }
        /* Speed control */
        .speed-row {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }
        .speed-row label { font-size: 0.85em; color: #8b949e; }
        .speed-row input[type="range"] {
            flex: 1;
            height: 6px;
            -webkit-appearance: none;
            background: #30363d;
            border-radius: 3px;
        }
        .speed-row input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #e3b341;
            cursor: pointer;
        }
        .speed-val { font-family: monospace; color: #e3b341; font-weight: bold; width: 40px; }
        /* Gripper */
        .gripper-row {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 8px 0;
        }
        .gripper-row input[type="range"] {
            flex: 1;
            height: 6px;
            -webkit-appearance: none;
            background: #30363d;
            border-radius: 3px;
        }
        .gripper-row input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #2ea043;
            cursor: pointer;
        }
        /* Log */
        .log-area {
            background: #0d1117;
            border: 1px solid #21262d;
            border-radius: 8px;
            padding: 10px;
            height: 160px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.8em;
        }
        .log-entry { margin: 2px 0; }
        .log-entry.success { color: #3fb950; }
        .log-entry.error { color: #f85149; }
        .log-entry.info { color: #58a6ff; }
        .log-entry.warn { color: #e3b341; }
        /* Jog buttons */
        .jog-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 4px;
            margin-bottom: 4px;
        }
        .jog-btn {
            padding: 6px 2px;
            border: 1px solid #30363d;
            border-radius: 6px;
            background: #21262d;
            color: #e6edf3;
            cursor: pointer;
            font-size: 0.75em;
            font-weight: 600;
            text-align: center;
            transition: background 0.15s;
        }
        .jog-btn:hover { background: #30363d; }
        .jog-btn:active { background: #1f6feb; }
        .jog-btn.plus { color: #3fb950; }
        .jog-btn.minus { color: #f85149; }
        @media (max-width: 1100px) {
            .main-layout { grid-template-columns: 1fr; }
            .cameras-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Piper Robot Web Control</h1>
        <span class="status-badge status-disconnected" id="status-badge">Disconnected</span>
    </div>

    <div class="main-layout">
        <div class="left-col">
            <!-- Cameras -->
            <div class="cameras-grid">
                <div class="camera-card">
                    <div class="cam-label">Camera 1 - Orbbec Astra Pro HD</div>
                    <img src="/video_feed_1" alt="Orbbec Camera" id="cam1">
                </div>
                <div class="camera-card">
                    <div class="cam-label">Camera 2 - Intel RealSense 455f</div>
                    <img src="/video_feed_2" alt="RealSense Camera" id="cam2">
                </div>
            </div>

            <!-- Joint Positions -->
            <div class="panel">
                <h2>Joint Positions</h2>
                <div class="joints-grid">
                    <div class="joint-box"><div class="jlabel">J1 Base</div><div class="jvalue" id="j1">0.0</div></div>
                    <div class="joint-box"><div class="jlabel">J2 Shoulder</div><div class="jvalue" id="j2">0.0</div></div>
                    <div class="joint-box"><div class="jlabel">J3 Elbow</div><div class="jvalue" id="j3">0.0</div></div>
                    <div class="joint-box"><div class="jlabel">J4 Wrist1</div><div class="jvalue" id="j4">0.0</div></div>
                    <div class="joint-box"><div class="jlabel">J5 Wrist2</div><div class="jvalue" id="j5">0.0</div></div>
                    <div class="joint-box"><div class="jlabel">J6 Wrist3</div><div class="jvalue" id="j6">0.0</div></div>
                </div>
            </div>

            <!-- Joint Control Sliders -->
            <div class="panel">
                <h2>Joint Control</h2>
                <div class="joint-slider-group">
                    <div class="joint-slider-row">
                        <label>J1</label>
                        <input type="range" id="slider-j1" min="-180" max="180" value="0" step="1">
                        <span class="slider-val" id="sval-j1">0.0</span>
                    </div>
                    <div class="joint-slider-row">
                        <label>J2</label>
                        <input type="range" id="slider-j2" min="-180" max="180" value="0" step="1">
                        <span class="slider-val" id="sval-j2">0.0</span>
                    </div>
                    <div class="joint-slider-row">
                        <label>J3</label>
                        <input type="range" id="slider-j3" min="-180" max="180" value="0" step="1">
                        <span class="slider-val" id="sval-j3">0.0</span>
                    </div>
                    <div class="joint-slider-row">
                        <label>J4</label>
                        <input type="range" id="slider-j4" min="-180" max="180" value="0" step="1">
                        <span class="slider-val" id="sval-j4">0.0</span>
                    </div>
                    <div class="joint-slider-row">
                        <label>J5</label>
                        <input type="range" id="slider-j5" min="-180" max="180" value="0" step="1">
                        <span class="slider-val" id="sval-j5">0.0</span>
                    </div>
                    <div class="joint-slider-row">
                        <label>J6</label>
                        <input type="range" id="slider-j6" min="-180" max="180" value="0" step="1">
                        <span class="slider-val" id="sval-j6">0.0</span>
                    </div>
                </div>
                <!-- Jog buttons -->
                <div class="jog-grid">
                    <div class="jog-btn plus" onclick="jogJoint(1,+5)">J1 +</div>
                    <div class="jog-btn plus" onclick="jogJoint(2,+5)">J2 +</div>
                    <div class="jog-btn plus" onclick="jogJoint(3,+5)">J3 +</div>
                    <div class="jog-btn plus" onclick="jogJoint(4,+5)">J4 +</div>
                    <div class="jog-btn plus" onclick="jogJoint(5,+5)">J5 +</div>
                    <div class="jog-btn plus" onclick="jogJoint(6,+5)">J6 +</div>
                </div>
                <div class="jog-grid">
                    <div class="jog-btn minus" onclick="jogJoint(1,-5)">J1 -</div>
                    <div class="jog-btn minus" onclick="jogJoint(2,-5)">J2 -</div>
                    <div class="jog-btn minus" onclick="jogJoint(3,-5)">J3 -</div>
                    <div class="jog-btn minus" onclick="jogJoint(4,-5)">J4 -</div>
                    <div class="jog-btn minus" onclick="jogJoint(5,-5)">J5 -</div>
                    <div class="jog-btn minus" onclick="jogJoint(6,-5)">J6 -</div>
                </div>
                <div class="btn-row" style="margin-top: 10px;">
                    <button class="btn btn-send" onclick="sendSliders()">Send to Arm</button>
                    <button class="btn btn-reset" onclick="readCurrentToSliders()">Read Current</button>
                </div>
            </div>
        </div>

        <div class="right-col">
            <!-- Quick Controls -->
            <div class="panel">
                <h2>Quick Controls</h2>
                <div class="btn-row">
                    <button class="btn btn-home" onclick="goHome()">Home</button>
                    <button class="btn btn-stop" onclick="emergencyStop()">E-STOP</button>
                </div>
                <div class="btn-row">
                    <button class="btn btn-stop" style="background:#8b4513" onclick="clearEmergencyStop()">Clear E-Stop</button>
                </div>
            </div>

            <!-- Speed Control -->
            <div class="panel">
                <h2>Speed</h2>
                <div class="speed-row">
                    <label>Rate:</label>
                    <input type="range" id="speed-slider" min="10" max="100" value="50" step="5">
                    <span class="speed-val" id="speed-val">50%</span>
                </div>
            </div>

            <!-- Gripper -->
            <div class="panel">
                <h2>Gripper</h2>
                <div class="btn-row">
                    <button class="btn btn-gripper-open" onclick="gripperOpen()">Open</button>
                    <button class="btn btn-gripper-close" onclick="gripperClose()">Close</button>
                </div>
                <div class="gripper-row">
                    <label style="font-size:0.85em;color:#8b949e;">Position:</label>
                    <input type="range" id="gripper-slider" min="0" max="70000" value="0" step="1000">
                    <span style="font-family:monospace;width:50px;color:#2ea043;" id="gripper-val">0%</span>
                </div>
                <button class="btn btn-send" style="width:100%;margin-top:6px;" onclick="sendGripper()">Set Gripper</button>
            </div>

            <!-- Arm Status -->
            <div class="panel">
                <h2>Arm Status</h2>
                <div style="font-size:0.9em;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                        <span style="color:#8b949e;">Status:</span>
                        <span id="arm-status" style="color:#58a6ff;">--</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                        <span style="color:#8b949e;">Gripper:</span>
                        <span id="gripper-status" style="color:#2ea043;">0%</span>
                    </div>
                </div>
            </div>

            <!-- Log -->
            <div class="panel">
                <h2>Log</h2>
                <div class="log-area" id="log-area"></div>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let syncSliders = true;

        socket.on('connect', () => {
            log('Connected to server', 'success');
        });

        socket.on('disconnect', () => {
            log('Disconnected from server', 'error');
            document.getElementById('status-badge').textContent = 'Disconnected';
            document.getElementById('status-badge').className = 'status-badge status-disconnected';
        });

        socket.on('status_update', (data) => {
            // Update connection badge
            const badge = document.getElementById('status-badge');
            if (data.connected) {
                badge.textContent = 'Connected';
                badge.className = 'status-badge status-connected';
            } else {
                badge.textContent = 'Disconnected';
                badge.className = 'status-badge status-disconnected';
            }

            // Update joint values
            for (let i = 0; i < 6; i++) {
                document.getElementById('j' + (i+1)).textContent = data.joints[i].toFixed(1);
                // Sync sliders to actual position if not being controlled
                if (syncSliders) {
                    const slider = document.getElementById('slider-j' + (i+1));
                    slider.value = Math.round(data.joints[i]);
                    document.getElementById('sval-j' + (i+1)).textContent = data.joints[i].toFixed(1);
                }
            }

            // Update status text
            document.getElementById('arm-status').textContent = data.status;
            document.getElementById('gripper-status').textContent =
                Math.round(data.gripper / 700) + '%';
        });

        socket.on('log', (msg) => {
            log(msg.text, msg.type);
        });

        // Slider value display updates
        for (let i = 1; i <= 6; i++) {
            const slider = document.getElementById('slider-j' + i);
            const valEl = document.getElementById('sval-j' + i);
            slider.addEventListener('input', () => {
                valEl.textContent = parseFloat(slider.value).toFixed(1);
                syncSliders = false;
            });
        }

        document.getElementById('speed-slider').addEventListener('input', function() {
            document.getElementById('speed-val').textContent = this.value + '%';
            fetch('/api/speed', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({speed: parseInt(this.value)})
            });
        });

        document.getElementById('gripper-slider').addEventListener('input', function() {
            document.getElementById('gripper-val').textContent =
                Math.round(parseInt(this.value) / 700) + '%';
        });

        function log(text, type) {
            const logArea = document.getElementById('log-area');
            const entry = document.createElement('div');
            entry.className = 'log-entry ' + (type || 'info');
            const time = new Date().toLocaleTimeString();
            entry.textContent = '[' + time + '] ' + text;
            logArea.appendChild(entry);
            logArea.scrollTop = logArea.scrollHeight;
            // Keep log trimmed
            while (logArea.children.length > 100) {
                logArea.removeChild(logArea.firstChild);
            }
        }

        function apiPost(url, body) {
            return fetch(url, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(body || {})
            }).then(r => r.json());
        }

        function goHome() {
            log('Sending home command...', 'info');
            apiPost('/api/home').then(d => log(d.message, d.success ? 'success' : 'error'));
            syncSliders = true;
        }

        function emergencyStop() {
            log('EMERGENCY STOP!', 'error');
            apiPost('/api/estop').then(d => log(d.message, d.success ? 'warn' : 'error'));
        }

        function clearEmergencyStop() {
            log('Clearing emergency stop...', 'info');
            apiPost('/api/estop/clear').then(d => log(d.message, d.success ? 'success' : 'error'));
        }

        function gripperOpen() {
            document.getElementById('gripper-slider').value = 70000;
            document.getElementById('gripper-val').textContent = '100%';
            apiPost('/api/gripper', {position: 70000}).then(d => log(d.message, d.success ? 'success' : 'error'));
        }

        function gripperClose() {
            document.getElementById('gripper-slider').value = 0;
            document.getElementById('gripper-val').textContent = '0%';
            apiPost('/api/gripper', {position: 0}).then(d => log(d.message, d.success ? 'success' : 'error'));
        }

        function sendGripper() {
            const pos = parseInt(document.getElementById('gripper-slider').value);
            apiPost('/api/gripper', {position: pos}).then(d => log(d.message, d.success ? 'success' : 'error'));
        }

        function sendSliders() {
            const joints = [];
            for (let i = 1; i <= 6; i++) {
                joints.push(parseFloat(document.getElementById('slider-j' + i).value));
            }
            syncSliders = false;
            log('Moving to: [' + joints.map(j => j.toFixed(1)).join(', ') + ']', 'info');
            apiPost('/api/move_joints', {joints: joints})
                .then(d => {
                    log(d.message, d.success ? 'success' : 'error');
                    syncSliders = true;
                });
        }

        function readCurrentToSliders() {
            syncSliders = true;
            log('Synced sliders to current position', 'info');
        }

        function jogJoint(joint, delta) {
            const slider = document.getElementById('slider-j' + joint);
            const newVal = Math.max(-180, Math.min(180, parseInt(slider.value) + delta));
            slider.value = newVal;
            document.getElementById('sval-j' + joint).textContent = newVal.toFixed(1);
            syncSliders = false;

            // Send jog command immediately
            apiPost('/api/jog', {joint: joint, delta: delta})
                .then(d => {
                    if (!d.success) log(d.message, 'error');
                });
        }
    </script>
</body>
</html>
'''


# ============ Routes ============
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/video_feed_1')
def video_feed_1():
    return Response(generate_frames(camera1),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video_feed_2')
def video_feed_2():
    return Response(generate_frames(camera2),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/home', methods=['POST'])
def api_home():
    try:
        def do_home():
            success = go_home()
            socketio.emit('log', {
                'text': 'Home position reached!' if success else 'Home position timeout',
                'type': 'success' if success else 'warn'
            })
        threading.Thread(target=do_home, daemon=True).start()
        return jsonify({'success': True, 'message': 'Moving to home...'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/estop', methods=['POST'])
def api_estop():
    try:
        if piper:
            piper.EmergencyStop(0x01)
            robot_state['status'] = 'EMERGENCY STOP'
            return jsonify({'success': True, 'message': 'Emergency stop activated!'})
        return jsonify({'success': False, 'message': 'Robot not connected'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/estop/clear', methods=['POST'])
def api_estop_clear():
    try:
        if piper:
            piper.EmergencyStop(0x02)
            time.sleep(0.5)
            # Re-enable arm
            for i in range(50):
                if piper.EnablePiper():
                    break
                time.sleep(0.02)
            piper.ModeCtrl(0x01, 0x01, robot_state['speed'], 0x00)
            robot_state['status'] = 'Ready'
            return jsonify({'success': True, 'message': 'Emergency stop cleared, arm re-enabled'})
        return jsonify({'success': False, 'message': 'Robot not connected'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/speed', methods=['POST'])
def api_speed():
    try:
        data = request.json
        speed = int(data.get('speed', 50))
        speed = max(10, min(100, speed))
        robot_state['speed'] = speed
        return jsonify({'success': True, 'message': f'Speed set to {speed}%'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/gripper', methods=['POST'])
def api_gripper():
    try:
        if piper is None:
            return jsonify({'success': False, 'message': 'Robot not connected'})
        data = request.json
        position = int(data.get('position', 0))
        position = max(0, min(70000, position))
        robot_state['gripper'] = position

        # Send gripper command for a few iterations
        def send_gripper():
            for _ in range(25):
                piper.MotionCtrl_2(0x01, 0x01, robot_state['speed'], 0x00)
                piper.GripperCtrl(position, 200, 0x01, 0)
                time.sleep(0.02)

        threading.Thread(target=send_gripper, daemon=True).start()
        pct = round(position / 700)
        return jsonify({'success': True, 'message': f'Gripper set to {pct}%'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/move_joints', methods=['POST'])
def api_move_joints():
    try:
        if piper is None:
            return jsonify({'success': False, 'message': 'Robot not connected'})
        data = request.json
        joints_deg = data.get('joints', [0, 0, 0, 0, 0, 0])
        # Convert degrees to millidegrees
        joints_milli = [int(j * 1000) for j in joints_deg]

        def do_move():
            success = move_to_joints(joints_milli)
            socketio.emit('log', {
                'text': f'Move complete!' if success else 'Move timeout',
                'type': 'success' if success else 'warn'
            })

        threading.Thread(target=do_move, daemon=True).start()
        return jsonify({'success': True, 'message': f'Moving to {[round(j,1) for j in joints_deg]}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/jog', methods=['POST'])
def api_jog():
    try:
        if piper is None:
            return jsonify({'success': False, 'message': 'Robot not connected'})
        data = request.json
        joint_num = int(data.get('joint', 1))
        delta_deg = float(data.get('delta', 5))

        # Get current position and add delta
        current = get_joints_milli()
        delta_milli = int(delta_deg * 1000)
        current[joint_num - 1] += delta_milli

        def do_jog():
            move_to_joints(current)

        threading.Thread(target=do_jog, daemon=True).start()
        return jsonify({'success': True, 'message': f'Jog J{joint_num} by {delta_deg}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ============ Main ============
def main():
    global piper

    print("=" * 60)
    print("  PIPER ROBOT WEB CONTROL SERVER")
    print("=" * 60)

    # Check CAN interface
    print("\n[..] Checking CAN interface...")
    can_ok, can_msg = check_can_interface()
    print(f"     {can_msg}")
    if not can_ok:
        print("\n[ERROR] CAN interface not ready!")
        print("  Run: sudo ip link set can0 type can bitrate 1000000 && sudo ip link set can0 up")
        print("  Or:  bash configure_can.sh")
        sys.exit(1)

    # Connect to Piper arm
    print("\n[..] Connecting to Piper arm...")
    try:
        piper = C_PiperInterface_V2(CAN_INTERFACE)
        piper.ConnectPort()
        time.sleep(0.5)

        # Enable arm
        print("[..] Enabling arm...")
        timeout = time.time() + 10.0
        enabled = False
        while time.time() < timeout:
            if piper.EnablePiper():
                enabled = True
                break
            time.sleep(0.1)

        if enabled:
            print("[OK] Arm enabled")
        else:
            print("[WARN] Arm enable timeout, continuing...")

        piper.ModeCtrl(0x01, 0x01, MOVE_SPD_RATE, 0x00)
        robot_state['connected'] = True
        robot_state['status'] = 'Ready'
        print("[OK] Piper arm connected")
    except Exception as e:
        print(f"[ERROR] Arm connection failed: {e}")
        robot_state['status'] = 'Arm disconnected'

    # Start cameras
    print("\n[..] Starting cameras...")
    camera1.start()
    camera2.start()
    time.sleep(1)

    # Start status update thread
    status_thread = threading.Thread(target=status_update_loop, daemon=True)
    status_thread.start()

    # Get network IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"

    print("\n" + "=" * 60)
    print("  WEB SERVER READY")
    print("=" * 60)
    print(f"  Local:   http://localhost:{SERVER_PORT}")
    print(f"  Network: http://{local_ip}:{SERVER_PORT}")
    print("=" * 60)
    print("\n  Open the URL above in a browser on any computer")
    print("  on the same network to control the robot.")
    print("\n  Press Ctrl+C to stop\n")

    # Run Flask
    socketio.run(app, host='0.0.0.0', port=SERVER_PORT, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[STOPPED] Shutting down...")
        camera1.stop()
        camera2.stop()
