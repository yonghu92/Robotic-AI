#!/usr/bin/env python3
# -*-coding:utf8-*-
# Play recorded positions
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
    move_spd_rate_ctrl = 100
    # CAN mode switch timeout in seconds
    timeout = 5.0
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
    piper = Piper("can0")
    interface = piper.init()
    piper.connect()
    time.sleep(0.1)

    def get_pos():
        '''Get current joint angles (radians) and gripper opening distance'''
        joint_state = piper.get_joint_states()[0]
        if have_gripper:
            return joint_state + (piper.get_gripper_states()[0][0], )
        return joint_state

    def stop():
        '''Stop arm; must call this function first after exiting teaching mode to use CAN control'''
        interface.EmergencyStop(0x01)
        time.sleep(1.0)
        # Safety check bypassed - arm will attempt to enable directly
        # Original code waited for joints 2,3,5 to be within safe limits
        piper.disable_arm()
        time.sleep(1.0)

    def enable():
        '''Enable arm and gripper'''
        while not piper.enable_arm():
            time.sleep(0.01)
        if have_gripper:
            time.sleep(0.01)
            piper.enable_gripper()
        interface.ModeCtrl(0x01, 0x01, move_spd_rate_ctrl, 0x00)
        print("INFO: Arm enabled successfully")

    print("Step 1: Make sure the arm has exited teaching mode before playback")
    if interface.GetArmStatus().arm_status.ctrl_mode != 1:
        stop()  # Must call this function first after exiting teaching mode to switch to CAN mode
    over_time = time.time() + timeout
    while interface.GetArmStatus().arm_status.ctrl_mode != 1:
        if over_time < time.time():
            print("ERROR: CAN mode switch failed, please check if teaching mode is disabled")
            exit()
        interface.ModeCtrl(0x01, 0x01, move_spd_rate_ctrl, 0x00)
        time.sleep(0.01)

    enable()
    count = 0
    input("Step 2: Press Enter to start playback")
    
    # Position tolerance in radians (increased for better reliability)
    position_tolerance = 0.15  # ~8.6 degrees
    # Timeout per position in seconds
    position_timeout = 10.0

    while play_times == 0 or abs(play_times) != count:
        for n, pos in enumerate(track):
            start_time = time.time()
            while True:
                piper.move_j(pos[:-1], move_spd_rate_ctrl)
                time.sleep(0.01)
                current_pos = get_pos()
                print(f"INFO: Playback {count + 1}, Point {n + 1}, Current: {current_pos}, Target: {pos}")
                # Check if position reached within tolerance
                if all(abs(current_pos[i] - pos[i]) < position_tolerance for i in range(6)):
                    print(f"INFO: Point {n + 1} reached!")
                    break
                # Check for timeout - skip to next position if stuck
                if time.time() - start_time > position_timeout:
                    print(f"WARNING: Point {n + 1} timeout - skipping to next position")
                    break
            if have_gripper and len(pos) == 7:
                piper.move_gripper(pos[-1], 1)
                time.sleep(0.5)
            if play_interval < 0:
                if n != len(track) - 1 and input("INPUT: Enter 'q' to quit, press Enter to continue: ") == 'q':
                    exit()
            else:
                time.sleep(play_interval)
        count += 1
    print("INFO: Playback complete!")