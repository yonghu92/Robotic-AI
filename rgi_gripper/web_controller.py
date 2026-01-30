#!/usr/bin/env python3
"""
Web Controller for Piper Arm + RGI Gripper
Provides web interface with live camera feed and robot controls
"""

import os
import sys
import time
import json
import threading
from flask import Flask, render_template_string, Response, jsonify, request
from flask_socketio import SocketIO, emit
import cv2
import numpy as np

# Add parent path for piper_sdk
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Using OpenCV directly for Orbbec camera
print("[INFO] Using OpenCV for Orbbec camera")

from piper_sdk import *
import serial
import struct

# ============ Configuration ============
POSITIONS_FILE = os.path.join(os.path.dirname(__file__), "saved_positions.json")
RGI_SERIAL_PORT = '/dev/ttyUSB1'
RGI_BAUDRATE = 115200
MOVE_SPD_RATE = 50

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'piper-robot-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
robot_state = {
    'connected': False,
    'joints': [0, 0, 0, 0, 0, 0],
    'gripper_pos': 0,
    'rotation_angle': 0,
    'status': 'Disconnected',
    'current_trajectory': None
}

piper = None
rgi = None
camera_frame = None
camera_lock = threading.Lock()


# ============ RGI Gripper Class ============
class RGIGripper:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.lock = threading.Lock()

    def calc_crc16(self, data):
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def build_cmd(self, slave_id, func, reg, value):
        if value < 0:
            value = value & 0xFFFF
        cmd = struct.pack('>BBHH', slave_id, func, reg, value)
        crc = self.calc_crc16(cmd)
        return cmd + struct.pack('<H', crc)

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            time.sleep(0.1)
            # Initialize
            self._write_reg(0x0100, 0xA5)
            time.sleep(0.5)
            self._write_reg(0x0104, 100)
            self._write_reg(0x0101, 100)
            self._write_reg(0x0107, 100)
            self._write_reg(0x0108, 100)
            return True
        except Exception as e:
            print(f"[WARN] RGI: {e}")
            return False

    def _write_reg(self, reg, value):
        if not self.ser:
            return
        cmd = self.build_cmd(1, 0x06, reg, int(value))
        self.ser.reset_input_buffer()
        self.ser.write(cmd)
        time.sleep(0.02)
        try:
            self.ser.read(100)
        except:
            pass

    def close_gripper(self):
        with self.lock:
            self._write_reg(0x0103, 0)

    def open_gripper(self):
        with self.lock:
            self._write_reg(0x0103, 1000)

    def rotate(self, degrees):
        with self.lock:
            self._write_reg(0x0109, int(degrees))

    def close(self):
        if self.ser:
            self.ser.close()


# ============ Camera Handler ============
class CameraHandler:
    def __init__(self):
        self.frame = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.cap = None

    def start(self):
        self.running = True
        # Always use OpenCV for Orbbec camera
        self.thread = threading.Thread(target=self._opencv_loop, daemon=True)
        self.thread.start()
        print("[OK] Camera thread started")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def _opencv_loop(self):
        """Get frames directly from Orbbec camera via OpenCV"""
        print("[..] Opening Orbbec camera at /dev/video4...")

        self.cap = cv2.VideoCapture('/dev/video4', cv2.CAP_V4L2)

        if not self.cap.isOpened():
            print("[WARN] /dev/video4 failed, trying index 4...")
            self.cap = cv2.VideoCapture(4)

        if not self.cap.isOpened():
            print("[WARN] Index 4 failed, trying index 0...")
            self.cap = cv2.VideoCapture(0)

        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            print("[OK] Camera opened successfully")
        else:
            print("[ERROR] Could not open any camera!")

        frame_count = 0
        error_count = 0

        while self.running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self.lock:
                        self.frame = frame.copy()
                    frame_count += 1
                    error_count = 0
                else:
                    error_count += 1
                    if error_count > 30:
                        print(f"[WARN] Too many camera errors, reconnecting...")
                        self.cap.release()
                        time.sleep(1)
                        self.cap = cv2.VideoCapture('/dev/video4', cv2.CAP_V4L2)
                        error_count = 0
            else:
                # No camera - show placeholder
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(placeholder, "Camera Not Available", (150, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                with self.lock:
                    self.frame = placeholder

            time.sleep(0.03)  # ~30 FPS

        if self.cap:
            self.cap.release()
        print(f"[INFO] Camera stopped after {frame_count} frames")

    def get_frame(self):
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
            else:
                # Return placeholder if no frame yet
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(placeholder, "Waiting for camera...", (170, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                return placeholder


camera = CameraHandler()


# ============ Robot Functions ============
def get_joints_milli():
    if piper is None:
        return [0, 0, 0, 0, 0, 0]
    js = piper.GetArmJointMsgs().joint_state
    return [js.joint_1, js.joint_2, js.joint_3, js.joint_4, js.joint_5, js.joint_6]


def get_joints_radians():
    if piper is None:
        return [0, 0, 0, 0, 0, 0]
    js = piper.GetArmJointMsgs().joint_state
    return [getattr(js, f"joint_{i+1}") / 1e3 * 0.0174533 for i in range(6)]


def move_to_joints(joints_milli, timeout=5.0):
    if piper is None:
        return False

    start = time.time()
    while time.time() - start < timeout:
        piper.MotionCtrl_2(0x01, 0x01, MOVE_SPD_RATE, 0x00)
        piper.JointCtrl(*joints_milli)
        time.sleep(0.02)

        current = get_joints_milli()
        errors = [abs(c - t) for c, t in zip(current, joints_milli)]
        if all(e < 1000 for e in errors):
            return True
    return False


def go_home():
    if rgi:
        rgi.open_gripper()
        time.sleep(0.3)
    return move_to_joints([0, 0, 0, 0, 0, 0])


def load_trajectories():
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_trajectories(data):
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


# ============ Status Update Thread ============
def status_update_loop():
    while True:
        if piper is not None:
            joints = get_joints_milli()
            robot_state['joints'] = [j / 1000 for j in joints]  # Convert to degrees
            robot_state['connected'] = True

        socketio.emit('status_update', robot_state)
        time.sleep(0.2)


# ============ Video Stream ============
def generate_frames():
    print("[OK] Video stream started")
    while True:
        try:
            frame = camera.get_frame()

            # Add overlay with joint info
            cv2.putText(frame, f"Joints: {[f'{j:.1f}' for j in robot_state['joints']]}",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.putText(frame, f"Status: {robot_state['status']}",
                       (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except Exception as e:
            print(f"[WARN] Frame error: {e}")

        time.sleep(0.05)  # ~20 FPS


# ============ HTML Template ============
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Piper Robot Controller</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 {
            text-align: center;
            margin-bottom: 20px;
            color: #00d4ff;
            text-shadow: 0 0 10px rgba(0,212,255,0.5);
        }
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 400px;
            gap: 20px;
        }
        .video-container {
            background: #0f0f1a;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .video-container img {
            width: 100%;
            height: auto;
            display: block;
        }
        .panel {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }
        .panel h2 {
            color: #00d4ff;
            margin-bottom: 15px;
            font-size: 1.2em;
            border-bottom: 1px solid rgba(0,212,255,0.3);
            padding-bottom: 10px;
        }
        .status-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 20px;
        }
        .status-item {
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }
        .status-item .label { font-size: 0.8em; color: #888; }
        .status-item .value { font-size: 1.2em; color: #00d4ff; font-weight: bold; }
        .btn {
            width: 100%;
            padding: 12px;
            margin: 5px 0;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            font-weight: bold;
            transition: all 0.3s;
        }
        .btn-primary { background: #00d4ff; color: #000; }
        .btn-primary:hover { background: #00a8cc; transform: scale(1.02); }
        .btn-success { background: #00ff88; color: #000; }
        .btn-success:hover { background: #00cc6a; }
        .btn-warning { background: #ffaa00; color: #000; }
        .btn-warning:hover { background: #cc8800; }
        .btn-danger { background: #ff4444; color: #fff; }
        .btn-danger:hover { background: #cc3333; }
        .btn-secondary { background: #444; color: #fff; }
        .btn-secondary:hover { background: #555; }
        .input-group {
            display: flex;
            gap: 10px;
            margin: 10px 0;
        }
        .input-group input {
            flex: 1;
            padding: 10px;
            border: 1px solid #333;
            border-radius: 8px;
            background: rgba(0,0,0,0.3);
            color: #fff;
        }
        .input-group select {
            padding: 10px;
            border: 1px solid #333;
            border-radius: 8px;
            background: rgba(0,0,0,0.3);
            color: #fff;
        }
        .trajectory-list {
            max-height: 200px;
            overflow-y: auto;
            margin: 10px 0;
        }
        .trajectory-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            margin: 5px 0;
        }
        .trajectory-item:hover {
            background: rgba(0,212,255,0.2);
        }
        .trajectory-item .name { font-weight: bold; }
        .trajectory-item .info { font-size: 0.8em; color: #888; }
        .log-area {
            background: rgba(0,0,0,0.5);
            border-radius: 8px;
            padding: 10px;
            height: 150px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.9em;
        }
        .log-entry { margin: 2px 0; }
        .log-entry.success { color: #00ff88; }
        .log-entry.error { color: #ff4444; }
        .log-entry.info { color: #00d4ff; }
        .connected { color: #00ff88; }
        .disconnected { color: #ff4444; }
        @media (max-width: 900px) {
            .main-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Piper Robot Controller</h1>

        <div class="main-grid">
            <div>
                <div class="video-container">
                    <img src="/video_feed" alt="Camera Feed">
                </div>

                <div class="panel" style="margin-top: 20px;">
                    <h2>📊 Joint Positions (degrees)</h2>
                    <div class="status-grid">
                        <div class="status-item"><div class="label">J1</div><div class="value" id="j1">0.0</div></div>
                        <div class="status-item"><div class="label">J2</div><div class="value" id="j2">0.0</div></div>
                        <div class="status-item"><div class="label">J3</div><div class="value" id="j3">0.0</div></div>
                        <div class="status-item"><div class="label">J4</div><div class="value" id="j4">0.0</div></div>
                        <div class="status-item"><div class="label">J5</div><div class="value" id="j5">0.0</div></div>
                        <div class="status-item"><div class="label">J6</div><div class="value" id="j6">0.0</div></div>
                    </div>
                </div>
            </div>

            <div>
                <div class="panel">
                    <h2>⚡ Status</h2>
                    <div class="status-item" style="margin-bottom: 15px;">
                        <div class="label">Connection</div>
                        <div class="value" id="connection-status">Connecting...</div>
                    </div>
                </div>

                <div class="panel" style="margin-top: 15px;">
                    <h2>🏠 Basic Controls</h2>
                    <button class="btn btn-primary" onclick="goHome()">🏠 Go Home</button>
                    <button class="btn btn-success" onclick="openGripper()">✋ Open Gripper</button>
                    <button class="btn btn-warning" onclick="closeGripper()">✊ Close Gripper</button>

                    <h3 style="margin-top: 15px; margin-bottom: 10px; font-size: 0.9em;">Rotate Gripper</h3>
                    <div class="input-group">
                        <input type="number" id="rotate-degrees" value="90" placeholder="Degrees">
                        <select id="rotate-dir">
                            <option value="cw">CW</option>
                            <option value="ccw">CCW</option>
                        </select>
                    </div>
                    <button class="btn btn-secondary" onclick="rotateGripper()">🔄 Rotate</button>
                </div>

                <div class="panel" style="margin-top: 15px;">
                    <h2>📁 Saved Trajectories</h2>
                    <div class="trajectory-list" id="trajectory-list">
                        Loading...
                    </div>
                    <button class="btn btn-primary" onclick="refreshTrajectories()">🔄 Refresh</button>
                </div>

                <div class="panel" style="margin-top: 15px;">
                    <h2>📝 Log</h2>
                    <div class="log-area" id="log-area"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const socket = io();

        socket.on('connect', () => {
            log('Connected to server', 'success');
        });

        socket.on('disconnect', () => {
            log('Disconnected from server', 'error');
        });

        socket.on('status_update', (data) => {
            document.getElementById('connection-status').textContent =
                data.connected ? 'Connected' : 'Disconnected';
            document.getElementById('connection-status').className =
                'value ' + (data.connected ? 'connected' : 'disconnected');

            for (let i = 0; i < 6; i++) {
                document.getElementById('j' + (i+1)).textContent =
                    data.joints[i].toFixed(1);
            }
        });

        socket.on('log', (msg) => {
            log(msg.text, msg.type);
        });

        function log(text, type = 'info') {
            const logArea = document.getElementById('log-area');
            const entry = document.createElement('div');
            entry.className = 'log-entry ' + type;
            entry.textContent = '[' + new Date().toLocaleTimeString() + '] ' + text;
            logArea.appendChild(entry);
            logArea.scrollTop = logArea.scrollHeight;
        }

        function goHome() {
            fetch('/api/home', { method: 'POST' })
                .then(r => r.json())
                .then(d => log(d.message, d.success ? 'success' : 'error'));
        }

        function openGripper() {
            fetch('/api/gripper/open', { method: 'POST' })
                .then(r => r.json())
                .then(d => log(d.message, d.success ? 'success' : 'error'));
        }

        function closeGripper() {
            fetch('/api/gripper/close', { method: 'POST' })
                .then(r => r.json())
                .then(d => log(d.message, d.success ? 'success' : 'error'));
        }

        function rotateGripper() {
            const degrees = document.getElementById('rotate-degrees').value;
            const dir = document.getElementById('rotate-dir').value;
            fetch('/api/gripper/rotate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ degrees: parseInt(degrees), direction: dir })
            })
            .then(r => r.json())
            .then(d => log(d.message, d.success ? 'success' : 'error'));
        }

        function refreshTrajectories() {
            fetch('/api/trajectories')
                .then(r => r.json())
                .then(data => {
                    const list = document.getElementById('trajectory-list');
                    if (Object.keys(data).length === 0) {
                        list.innerHTML = '<div style="color:#888;text-align:center;padding:20px;">No saved trajectories</div>';
                        return;
                    }
                    list.innerHTML = '';
                    for (const [name, info] of Object.entries(data)) {
                        const item = document.createElement('div');
                        item.className = 'trajectory-item';
                        item.innerHTML = `
                            <div>
                                <div class="name">${name}</div>
                                <div class="info">${info.trajectory ? info.trajectory.length : 0} points</div>
                            </div>
                            <div>
                                <button class="btn btn-success" style="width:auto;padding:5px 15px;margin:2px;"
                                    onclick="playTrajectory('${name}')">▶ Play</button>
                                <button class="btn btn-danger" style="width:auto;padding:5px 15px;margin:2px;"
                                    onclick="deleteTrajectory('${name}')">🗑</button>
                            </div>
                        `;
                        list.appendChild(item);
                    }
                });
        }

        function playTrajectory(name) {
            log('Playing trajectory: ' + name, 'info');
            fetch('/api/trajectory/play', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name })
            })
            .then(r => r.json())
            .then(d => log(d.message, d.success ? 'success' : 'error'));
        }

        function deleteTrajectory(name) {
            if (!confirm('Delete trajectory "' + name + '"?')) return;
            fetch('/api/trajectory/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name })
            })
            .then(r => r.json())
            .then(d => {
                log(d.message, d.success ? 'success' : 'error');
                if (d.success) refreshTrajectories();
            });
        }

        // Initial load
        refreshTrajectories();
    </script>
</body>
</html>
'''


# ============ Routes ============
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/home', methods=['POST'])
def api_home():
    try:
        robot_state['status'] = 'Going home...'
        socketio.emit('log', {'text': 'Moving to home position...', 'type': 'info'})
        success = go_home()
        robot_state['status'] = 'At home' if success else 'Home failed'
        return jsonify({'success': success, 'message': 'Moved to home position' if success else 'Failed to reach home'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/gripper/open', methods=['POST'])
def api_gripper_open():
    try:
        if rgi:
            rgi.open_gripper()
            return jsonify({'success': True, 'message': 'Gripper opened'})
        return jsonify({'success': False, 'message': 'RGI not connected'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/gripper/close', methods=['POST'])
def api_gripper_close():
    try:
        if rgi:
            rgi.close_gripper()
            return jsonify({'success': True, 'message': 'Gripper closed'})
        return jsonify({'success': False, 'message': 'RGI not connected'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/gripper/rotate', methods=['POST'])
def api_gripper_rotate():
    try:
        data = request.json
        degrees = data.get('degrees', 90)
        direction = data.get('direction', 'cw')

        if direction == 'ccw':
            degrees = -degrees

        if rgi:
            rgi.rotate(degrees)
            return jsonify({'success': True, 'message': f'Rotated {abs(degrees)}° {direction.upper()}'})
        return jsonify({'success': False, 'message': 'RGI not connected'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/trajectories', methods=['GET'])
def api_get_trajectories():
    return jsonify(load_trajectories())


@app.route('/api/trajectory/play', methods=['POST'])
def api_play_trajectory():
    try:
        data = request.json
        name = data.get('name')

        trajectories = load_trajectories()
        if name not in trajectories:
            return jsonify({'success': False, 'message': f'Trajectory "{name}" not found'})

        trajectory = trajectories[name].get('trajectory', [])
        if not trajectory:
            return jsonify({'success': False, 'message': 'Trajectory is empty'})

        robot_state['status'] = f'Playing: {name}'

        # Play in background thread
        def play():
            for i, pos in enumerate(trajectory):
                wait_time = pos[0]
                target_joints = pos[1:7]

                joints_milli = [round(r / 0.0174533 * 1000) for r in target_joints]
                piper.MotionCtrl_2(0x01, 0x01, MOVE_SPD_RATE, 0x00)
                piper.JointCtrl(*joints_milli)

                if i < len(trajectory) - 1:
                    time.sleep(wait_time)
                else:
                    time.sleep(0.5)

            robot_state['status'] = 'Trajectory complete'
            socketio.emit('log', {'text': f'Trajectory "{name}" complete!', 'type': 'success'})

        threading.Thread(target=play, daemon=True).start()
        return jsonify({'success': True, 'message': f'Playing trajectory "{name}" ({len(trajectory)} points)'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/trajectory/delete', methods=['POST'])
def api_delete_trajectory():
    try:
        data = request.json
        name = data.get('name')

        trajectories = load_trajectories()
        if name not in trajectories:
            return jsonify({'success': False, 'message': f'Trajectory "{name}" not found'})

        del trajectories[name]
        save_trajectories(trajectories)
        return jsonify({'success': True, 'message': f'Deleted trajectory "{name}"'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ============ Main ============
def main():
    global piper, rgi

    print("=" * 60)
    print("  PIPER ROBOT WEB CONTROLLER")
    print("=" * 60)

    # Connect to arm
    print("[..] Connecting to Piper arm...")
    try:
        piper = C_PiperInterface_V2("can0")
        piper.ConnectPort()
        time.sleep(0.1)

        # Enable arm
        timeout = time.time() + 10.0
        while not piper.EnablePiper():
            if time.time() > timeout:
                print("[ERROR] Failed to enable arm")
                break
            time.sleep(0.1)

        piper.ModeCtrl(0x01, 0x01, MOVE_SPD_RATE, 0x00)
        robot_state['connected'] = True
        robot_state['status'] = 'Connected'
        print("[OK] Piper arm connected")
    except Exception as e:
        print(f"[ERROR] Arm connection failed: {e}")
        robot_state['status'] = 'Arm disconnected'

    # Connect RGI
    print("[..] Connecting to RGI gripper...")
    rgi = RGIGripper(RGI_SERIAL_PORT, RGI_BAUDRATE)
    if rgi.connect():
        print("[OK] RGI gripper connected")
    else:
        print("[WARN] RGI gripper not connected")
        rgi = None

    # Start camera
    print("[..] Starting camera...")
    camera.start()
    print("[OK] Camera started")

    # Start status update thread
    status_thread = threading.Thread(target=status_update_loop, daemon=True)
    status_thread.start()

    # Get local IP
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print("\n" + "=" * 60)
    print("  WEB SERVER READY")
    print("=" * 60)
    print(f"  Local:   http://localhost:5000")
    print(f"  Network: http://{local_ip}:5000")
    print("=" * 60)
    print("\nPress Ctrl+C to stop\n")

    # Run Flask
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[STOPPED]")
        camera.stop()
        if rgi:
            rgi.close()
