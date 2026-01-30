#!/usr/bin/env python3
# -*-coding:utf8-*-
# Gamepad Control Script for Piper Robotic Arm
# Controls all 6 joints and gripper using a gamepad controller

import time
import pygame
from piper_sdk import C_PiperInterface_V2

print("=== Gamepad Control Script ===")

# Initialize pygame and joystick
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("No joystick found!")
    exit(1)
    
else:
    joystick = pygame.joystick.Joystick(0)
    
    joystick.init()
    print(f"Joystick connected: {joystick.get_name()}")
    print(f"Axes: {joystick.get_numaxes()}, Buttons: {joystick.get_numbuttons()}")

# Initialize and connect to Piper arm
piper = C_PiperInterface_V2("can0")

piper.ConnectPort()
time.sleep(0.5)

# Check current status
status = piper.GetArmStatus()
print(f"Current control mode: {status.arm_status.ctrl_mode}")
print(f"Arm status: {status.arm_status.arm_status}")

# Clear emergency stop if arm is in that state
if status.arm_status.arm_status == 1:  # EMERGENCY_STOP
    response = input("\nArm is in EMERGENCY_STOP state. Clear it? (y/n): ").strip().lower()
    if response == 'y':
        piper.EmergencyStop(0x02)  # Clear emergency stop
        time.sleep(1.0)
        print("Emergency stop cleared!")
    else:
        print("Cannot proceed with emergency stop active. Exiting.")
        exit(1)

# Step 1: Set to CAN control mode
print("\nStep 1: Setting CAN control mode...")
for i in range(50):
    piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
    time.sleep(0.1)
    if piper.GetArmStatus().arm_status.ctrl_mode == 1:
        print("CAN mode activated!")
        break
else:
    print("WARNING: Could not switch to CAN mode, continuing anyway...")

# Step 2: Enable all motors
print("Step 2: Enabling motors...")
for i in range(100):
    piper.EnableArm(7)  # Enable all 7 motors (6 joints + gripper)
    time.sleep(0.1)
    enable_status = piper.GetArmEnableStatus()
    if all(enable_status):
        print(f"All motors enabled: {enable_status}")
        break
    if i % 10 == 0:
        print(f"Enabling... attempt {i+1}, status: {enable_status}")
else:
    print(f"WARNING: Not all motors enabled: {enable_status}")
    print("The arm may need to be manually moved to a safe position first.")
    print("Try manually moving the arm closer to an upright position.")
    exit(1)

# Step 3: Move to home position (all joints to 0)
print("\nStep 3: Moving to home position...")
print("WARNING: Arm will move! Make sure the area is clear.")
response = input("Press Enter to continue or Ctrl+C to cancel...")

home_joints = [0, 0, 0, 0, 0, 0]  # All joints at 0 degrees

for i in range(500):
    piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
    piper.JointCtrl(*home_joints)
    time.sleep(0.02)

    # Check if we're close to home
    joints = piper.GetArmJointMsgs().joint_state
    current = [
        joints.joint_1 / 1000,
        joints.joint_2 / 1000,
        joints.joint_3 / 1000,
        joints.joint_4 / 1000,
        joints.joint_5 / 1000,
        joints.joint_6 / 1000,
    ]

    if i % 50 == 0:
        print(f"Current position: {[round(j, 1) for j in current]} deg")

    # Check if close enough to home (within 5 degrees)
    if all(abs(c) < 5 for c in current):
        print("\n=== Arm is at home position! ===")
        break
else:
    print("\nTimeout - arm may not have reached home position")
    joints = piper.GetArmJointMsgs().joint_state
    print(f"Final position: joint1={joints.joint_1/1000:.1f}, joint2={joints.joint_2/1000:.1f}, "
          f"joint3={joints.joint_3/1000:.1f}, joint4={joints.joint_4/1000:.1f}, "
          f"joint5={joints.joint_5/1000:.1f}, joint6={joints.joint_6/1000:.1f}")

# Re-enable arm before starting control (REQUIRED for JointCtrl to work!)
print("\nRe-enabling arm for control...")
enabled = False
for i in range(50):
    if piper.EnablePiper():
        enabled = True
        print("✓ Enabled!")
        break
    time.sleep(0.02)

if not enabled:
    print("⚠ Warning: EnablePiper timed out, continuing anyway...")

# Set to joint control mode
piper.ModeCtrl(0x01, 0x01, 30, 0x00)
time.sleep(0.2)

# Get current joint positions
print("\n=== Starting J1, J2, J3, J4, J5 & J6 Control ===")
print("Left Stick X = Rotate Joint 1 (base rotation)")
print("Left Stick Y = Rotate Joint 2 (arm lifting)")
print("Right Stick Y (UP/DOWN) = Rotate Joint 3 (elbow)")
print("Right Stick X (LEFT/RIGHT) = Rotate Joint 4 (wrist yaw)")
print("D-Pad UP/DOWN = Rotate Joint 5 (wrist pitch)")
print("D-Pad LEFT/RIGHT = Rotate Joint 6 (wrist rotation)")
print("Button 6 (Back) = Open Gripper (hold to open)")
print("Button 7 (Start) = Close Gripper (hold to close)")
print("Button LB (4) = Decrease Overall Speed (all joints)")
print("Button RB (5) = Increase Overall Speed (all joints)")
print("Button R3 (9) = Go to Home Position")
print("Press Ctrl+C to stop\n")

joints = piper.GetArmJointMsgs()
j1 = joints.joint_state.joint_1  # Current J1 position in millidegrees
j2 = joints.joint_state.joint_2
j3 = joints.joint_state.joint_3
j4 = joints.joint_state.joint_4
j5 = joints.joint_state.joint_5
j6 = joints.joint_state.joint_6

print(f"Starting J1: {j1/1000:.1f}°, J2: {j2/1000:.1f}°, J3: {j3/1000:.1f}°, J4: {j4/1000:.1f}°, J5: {j5/1000:.1f}°, J6: {j6/1000:.1f}°")

# Control parameters
SPEED = 500  # millidegrees per loop (0.5 degrees per loop)

# Main control loop - J1 & J2 control with D-pad and Left Stick
try:
    DEADZONE = 0.1  # Deadzone for left stick to avoid drift
    STICK_SCALE = 2.0  # Scale factor for left stick sensitivity
    
    # Gripper state (range: 0 = closed, 70000 = fully open, in micrometers)
    gripper_state = 0  # 0 = closed, 70000 = fully open
    GRIPPER_STEP = 1500  # Step size for gripper movement per loop
    
    # Overall speed multiplier for all joints (adjustable with LB/RB buttons)
    speed_multiplier = 1.0  # Initial speed multiplier (1.0 = 100%)
    speed_multiplier_min = 0.25  # Minimum speed (25%)
    speed_multiplier_max = 1.0  # Maximum speed (100%)
    speed_multiplier_step = 0.25  # Speed change per button press (25%)
    last_lb_button = False
    last_rb_button = False
    last_r3_button = False
    
    while True:
        pygame.event.pump()
        
        # Get D-pad input (hat 0)
        # hat[0] = -1 (LEFT), 0 (none), 1 (RIGHT)
        # hat[1] = -1 (DOWN), 0 (none), 1 (UP)
        if joystick.get_numhats() > 0:
            hat = joystick.get_hat(0)
            dpad_x = hat[0]  # LEFT/RIGHT
            dpad_y = hat[1]  # UP/DOWN
        else:
            dpad_x = 0
            dpad_y = 0
        
        # Get Left Stick input (axes 0 and 1)
        # axis 0 = X (LEFT = -1.0, RIGHT = +1.0)
        # axis 1 = Y (UP = -1.0, DOWN = +1.0) - Note: pygame Y is inverted
        if joystick.get_numaxes() >= 2:
            stick_x = joystick.get_axis(0)  # Left stick X
            stick_y = joystick.get_axis(1)  # Left stick Y
            
            # Apply deadzone
            if abs(stick_x) < DEADZONE:
                stick_x = 0.0
            if abs(stick_y) < DEADZONE:
                stick_y = 0.0
        else:
            stick_x = 0.0
            stick_y = 0.0
        
        # Get Right Stick input (axes 2 and 3) - Linux mapping (based on test_controller.py)
        # axis 2 = X (LEFT = -1.0, RIGHT = +1.0)
        # axis 3 = Y (UP = -1.0, DOWN = +1.0) - Note: pygame Y is inverted, will be inverted
        if joystick.get_numaxes() >= 4:
            right_stick_x = joystick.get_axis(2)  # Right stick X (axis 2)
            right_stick_y = -joystick.get_axis(3)  # Right stick Y (axis 3, inverted)
            
            # Apply deadzone
            if abs(right_stick_x) < DEADZONE:
                right_stick_x = 0.0
            if abs(right_stick_y) < DEADZONE:
                right_stick_y = 0.0
        else:
            right_stick_x = 0.0
            right_stick_y = 0.0
        
        # Overall speed control for all joints using LB (button 4) and RB (button 5)
        lb_button = joystick.get_button(4)  # LB button - decrease overall speed
        rb_button = joystick.get_button(5)  # RB button - increase overall speed
        
        # Adjust speed multiplier on button press (edge detection)
        if lb_button and not last_lb_button:
            # LB pressed - decrease overall speed
            speed_multiplier = max(speed_multiplier_min, speed_multiplier - speed_multiplier_step)
        if rb_button and not last_rb_button:
            # RB pressed - increase overall speed
            speed_multiplier = min(speed_multiplier_max, speed_multiplier + speed_multiplier_step)
        
        last_lb_button = lb_button
        last_rb_button = rb_button
        
        # Update J1 based on Left Stick X only (with overall speed multiplier)
        if abs(stick_x) > 0:
            # Scale stick input: -1.0 to +1.0 -> -SPEED*STICK_SCALE*speed_multiplier to +SPEED*STICK_SCALE*speed_multiplier
            j1 += int(stick_x * SPEED * STICK_SCALE * speed_multiplier)
        
        # Update J2 based on Left Stick Y only (with overall speed multiplier)
        # Note: pygame Y axis is inverted (UP = -1.0), so we negate it
        if abs(stick_y) > 0:
            # Invert Y axis and scale: -1.0 to +1.0 -> +SPEED*STICK_SCALE*speed_multiplier to -SPEED*STICK_SCALE*speed_multiplier
            j2 -= int(stick_y * SPEED * STICK_SCALE * speed_multiplier)
        
        # Update J3 based on Right Stick Y (UP/DOWN) (with overall speed multiplier)
        # Note: right_stick_y is already inverted when reading from axis 3
        if abs(right_stick_y) > 0:
            j3 += int(right_stick_y * SPEED * STICK_SCALE * speed_multiplier)
        
        # Update J4 based on Right Stick X (LEFT/RIGHT) (with overall speed multiplier)
        if abs(right_stick_x) > 0:
            j4 += int(right_stick_x * SPEED * STICK_SCALE * speed_multiplier)
        
        # Update J5 based on D-pad UP/DOWN (digital: 0 or 1, with overall speed multiplier)
        if dpad_y != 0:
            j5 += int(dpad_y * SPEED * speed_multiplier)
        
        # Update J6 based on D-pad LEFT/RIGHT (digital: 0 or 1, with overall speed multiplier)
        if dpad_x != 0:
            j6 += int(dpad_x * SPEED * speed_multiplier)
        
        # Home position control with R3 button (button 9)
        r3_button = joystick.get_button(9)  # R3 button - go to home position
        if r3_button and not last_r3_button:
            print("\n>>> GOING TO HOME POSITION <<<")
            j1, j2, j3, j4, j5, j6 = 0, 0, 0, 0, 0, 0
        last_r3_button = r3_button
        
        # Gripper control with buttons 6 (Back) and 7 (Start)
        # Move gripper only while button is pressed, stop when released
        back_button = joystick.get_button(6)  # Back button - open gripper
        start_button = joystick.get_button(7)  # Start button - close gripper
        
        # Continuous control: move gripper while button is held
        if back_button:
            # Button 6 (Back) held - open gripper (increase)
            gripper_state = min(70000, gripper_state + GRIPPER_STEP)
        elif start_button:
            # Button 7 (Start) held - close gripper (decrease)
            gripper_state = max(0, gripper_state - GRIPPER_STEP)
        # If neither button is pressed, gripper_state stays the same (stops moving)
        
        # Keep sending mode control command (like in home position code)
        piper.MotionCtrl_2(0x01, 0x01, 30, 0x00)
        
        # Send joint control command (keep other joints at current position)
        piper.JointCtrl(j1, j2, j3, j4, j5, j6)
        
        # Send gripper control command (gripper_state: 0=closed, 70000=open, speed: 200, mode: 0x01)
        piper.GripperCtrl(gripper_state, 200, 0x01, 0)
        
        # Display current joint angles
        dpad_str = ""
        if dpad_x == -1:
            dpad_str += "LEFT "
        elif dpad_x == 1:
            dpad_str += "RIGHT "
        if dpad_y == 1:
            dpad_str += "UP "
        elif dpad_y == -1:
            dpad_str += "DOWN "
        if not dpad_str:
            dpad_str = "(none)"
        
        left_stick_str = ""
        if abs(stick_x) > DEADZONE or abs(stick_y) > DEADZONE:
            left_stick_str = f"L: X={stick_x:+.2f} Y={stick_y:+.2f}"
        
        right_stick_str = ""
        if abs(right_stick_x) > DEADZONE or abs(right_stick_y) > DEADZONE:
            right_stick_str = f"R: X={right_stick_x:+.2f} Y={right_stick_y:+.2f}"
        
        gripper_percent = int((gripper_state / 70000) * 100) if gripper_state > 0 else 0
        gripper_str = f"Gripper: {gripper_percent}%"
        speed_str = f"Speed: {int(speed_multiplier * 100)}%"
        print(f"\rJ1: {j1/1000:+.1f}°  J2: {j2/1000:+.1f}°  J3: {j3/1000:+.1f}°  J4: {j4/1000:+.1f}°  J5: {j5/1000:+.1f}°  J6: {j6/1000:+.1f}°  {gripper_str}  {speed_str}  D-Pad: {dpad_str}  {left_stick_str}  {right_stick_str}  ", end="")
        
        time.sleep(0.02)
        
except KeyboardInterrupt:
    print("\n\nStopped!")

# Optional: Emergency stop
response = input("\nActivate emergency stop? (y/n): ").strip().lower()
if response == 'y':
    piper.EmergencyStop(0x01)  # Trigger emergency stop
    print("Emergency stop activated!")
else:
    print("Emergency stop skipped.")

# Cleanup
pygame.quit()
print("\nDone!")
