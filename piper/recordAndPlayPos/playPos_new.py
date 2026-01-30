#!/usr/bin/env python3
# -*-coding:utf8-*-
# Play recorded positions (V2 API)
import os, time, csv
from piper_sdk import *

if __name__ == "__main__":
    # Whether gripper is attached
    have_gripper = True
    # Number of playback times, 0 means infinite loop
    play_times = 1
    # Playback interval in seconds, negative means manual key control
    play_interval = 0
    # Movement speed percentage, recommended range: 10-100
    move_spd_rate_ctrl = 10 
    # CAN mode switch timeout in seconds
    timeout = 10.0
    # CSV file path to load positions
    CSV_path = os.path.join(os.path.dirname(__file__), "pos.csv")
    # Read positions file
    try:
        with open(CSV_path, 'r', encoding='utf-8') as f:
            track = list(csv.reader(f))
            if not track:
                print("ERROR: Position file is empty")
                exit()
            track = [[float(j) for j in i] for i in track]    # Convert to float list
    except FileNotFoundError:
        print("ERROR: Position file not found")
        exit()

    # Initialize and connect to robotic arm
    piper = C_PiperInterface_V2("can0")
    piper.ConnectPort()
    time.sleep(0.5)

    def get_pos():
        '''Get current joint angles (radians) and gripper opening distance'''
        joint_state = piper.GetArmJointMsgs().joint_state
        joint_state = tuple(getattr(joint_state, f"joint_{i+1}") / 1e3 * 0.0174533 for i in range(6))
        if have_gripper:
            return joint_state + (piper.GetArmGripperMsgs().gripper_state.grippers_angle / 1e6, )
        return joint_state

    def stop():
        '''Stop arm; must call after exiting teaching mode to use CAN control'''
        piper.EmergencyStop(0x01)
        time.sleep(1.0)
        # Safety check bypassed - recover arm directly
        piper.EmergencyStop(0x02)
        time.sleep(1.0)

    def enable():
        '''Enable arm and gripper'''
        print("INFO: Enabling arm...")
        enable_timeout = time.time() + 10.0
        while not piper.EnablePiper():
            if time.time() > enable_timeout:
                print("ERROR: Failed to enable arm")
                exit()
            time.sleep(0.1)
        if have_gripper:
            time.sleep(0.1)
            piper.GripperCtrl(0, 1000, 0x01, 0x00)
        piper.ModeCtrl(0x01, 0x01, move_spd_rate_ctrl, 0x00)
        print("INFO: Arm enabled successfully")

    print("Step 1: Make sure the arm has exited teaching mode before playback")
    if piper.GetArmStatus().arm_status.ctrl_mode != 1:
        stop()  # Must call this function first after exiting teaching mode to switch to CAN mode
    over_time = time.time() + timeout
    while piper.GetArmStatus().arm_status.ctrl_mode != 1:
        if over_time < time.time():
            print("ERROR: CAN mode switch failed, please check if teaching mode is disabled")
            exit()
        piper.ModeCtrl(0x01, 0x01, move_spd_rate_ctrl, 0x00)
        time.sleep(0.1)

    enable()
    count = 0
    input("Step 2: Press Enter to start playback")
    while play_times == 0 or abs(play_times) != count:
        for n, pos in enumerate(track):
            while True:
                joints = [round(i / 0.0174533 * 1e3) for i in pos[:-1]]
                piper.MotionCtrl_2(0x01, 0x01, move_spd_rate_ctrl, 0x00)
                piper.JointCtrl(*joints)
                time.sleep(0.01)
                current_pos = get_pos()
                print(f"INFO: Playback {count + 1}, Point {n + 1}, Current: {current_pos}, Target: {pos}")
                if all(abs(current_pos[i] - pos[i]) < 0.1 for i in range(6)):
                    break
            
            
                piper.GripperCtrl(round(pos[-1] * 1e6), 1000, 0x01, 0x00)
                time.sleep(0.5)
            if play_interval < 0:
                if n != len(track) - 1 and input("INPUT: Enter 'q' to quit, press Enter to continue: ") == 'q':
                    exit()
            else:
                time.sleep(play_interval)
        count += 1
    print("INFO: Playback complete")

    # Go to home position (all joints at 0)
    print("INFO: Moving to home position...")
    home_pos = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    while True:
        joints = [0, 0, 0, 0, 0, 0]  # All joints to 0
        piper.MotionCtrl_2(0x01, 0x01, move_spd_rate_ctrl, 0x00)
        piper.JointCtrl(*joints)
        time.sleep(0.01)
        current_pos = get_pos()
        print(f"INFO: Going home, Current: {current_pos[:6]}, Target: {home_pos}")
        if all(abs(current_pos[i] - home_pos[i]) < 0.1 for i in range(6)):
            break
    if have_gripper:
        piper.GripperCtrl(0, 1000, 0x01, 0x00)  # Open gripper
        time.sleep(0.5)
    print("INFO: Arm is now at home position")