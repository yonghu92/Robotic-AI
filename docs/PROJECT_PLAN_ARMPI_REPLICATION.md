# Project Plan: Replicating ArmPi Ultra Capabilities with Piper Arm

## Project Overview

**Objective:** Replicate the key capabilities of the ArmPi Ultra robotic arm system using the Piper 6-DOF arm and RealSense depth camera.

**Start Date:** 2026-01-21
**Status:** In Progress

---

## Final Goal

Build a complete vision-guided robotic manipulation system that can:
1. Detect objects (cubes, colors, shapes) using depth camera
2. Autonomously pick and place objects
3. Sort objects by color/type
4. Respond to voice commands
5. Operate through ROS2 with full simulation support

### Final Evaluation Criteria
- [ ] System can detect and locate objects with >90% accuracy
- [ ] Pick and place success rate >80%
- [ ] Color sorting works for at least 3 colors
- [ ] Voice commands trigger correct actions >90% of time
- [ ] Full demo can run autonomously for 10+ cycles without failure

---

## Current Assets (What We Have)

| Component | Status | Location/Notes |
|-----------|--------|----------------|
| Piper 6-DOF Arm | Working | CAN bus control via piper_sdk |
| RealSense Depth Camera | Working | RGB + Depth streams available |
| ROS2 Jazzy | Working | Installed and configured |
| URDF/RViz2 Simulation | Working | `piper_kinematics` package |
| IK Solver | Working | `piper_ik_node.py` |
| Sim-to-Real Bridge | Working | `sim_to_real_bridge.py` |
| Cube Detection | Partial | `cubeAndLineDet` package exists |
| Gripper Control | Available | Via piper_sdk |

---

## Project Phases

### Phase 1: Camera-Arm Calibration & Coordinate Transform
**Goal:** Accurately transform camera coordinates to arm base coordinates

#### Requirements
- [ ] RealSense camera mounted in fixed position relative to arm
- [ ] Calibration target (checkerboard or ArUco markers)
- [ ] Hand-eye calibration procedure

#### Tasks
| Task | Description | Status | Notes |
|------|-------------|--------|-------|
| 1.1 | Mount camera in fixed position (eye-to-hand or eye-in-hand) | **COMPLETE** | Eye-in-hand config (camera on arm head) |
| 1.2 | Create/obtain calibration target | **PENDING** | ChArUco board generator created, need to print |
| 1.3 | Implement camera intrinsic calibration | **COMPLETE** | Factory calibrated, saved to camera_intrinsics.yaml |
| 1.4 | Implement hand-eye calibration | **COMPLETE** | hand_eye_calibration.py created |
| 1.5 | Create coordinate transform node (camera → arm base) | Not Started | |
| 1.6 | Test transform accuracy | Not Started | |

#### Validation Criteria
- [ ] Camera intrinsics calibrated (reprojection error < 0.5 pixels)
- [ ] Point a known object, arm moves to within 1cm of actual position
- [ ] Transform works consistently across workspace

#### Deliverables
- `camera_calibration.yaml` - Camera intrinsic parameters
- `hand_eye_transform.yaml` - Camera to arm base transform
- `coordinate_transform_node.py` - ROS2 node for transforms

---

### Phase 2: Object Detection & Localization
**Goal:** Detect objects and get their 3D position in arm coordinates

#### Requirements
- [ ] Working camera stream (RGB + Depth)
- [ ] Object detection algorithm (color-based or ML-based)
- [ ] Depth-to-3D conversion
- [ ] Coordinate transform from Phase 1

#### Tasks
| Task | Description | Status | Notes |
|------|-------------|--------|-------|
| 2.1 | Verify RealSense RGB+Depth streams working | Not Started | |
| 2.2 | Implement color-based object detection | Not Started | Detect red, green, blue objects |
| 2.3 | Implement shape detection (cube, sphere, etc.) | Not Started | |
| 2.4 | Get object centroid in pixel coordinates | Not Started | |
| 2.5 | Convert pixel + depth to 3D point | Not Started | |
| 2.6 | Transform 3D point to arm base frame | Not Started | |
| 2.7 | Publish detected objects as ROS2 messages | Not Started | |
| 2.8 | Visualize detections in RViz2 | Not Started | |

#### Validation Criteria
- [ ] Detects colored cubes at various positions
- [ ] 3D position error < 2cm compared to ground truth
- [ ] Detection works at 10+ FPS
- [ ] Works under normal indoor lighting

#### Deliverables
- `object_detector_node.py` - ROS2 node for detection
- `DetectedObject.msg` - Custom message type
- Detection visualization in RViz2

---

### Phase 3: Gripper Control & Grasping
**Goal:** Reliably grasp and release objects

#### Requirements
- [ ] Gripper control via piper_sdk
- [ ] Grasp planning (approach angle, grip force)
- [ ] Object size estimation for grip width

#### Tasks
| Task | Description | Status | Notes |
|------|-------------|--------|-------|
| 3.1 | Test gripper open/close via SDK | Not Started | |
| 3.2 | Determine grip parameters for different objects | Not Started | |
| 3.3 | Create gripper control ROS2 service | Not Started | |
| 3.4 | Implement pre-grasp approach pose | Not Started | |
| 3.5 | Implement grasp sequence (approach → close → lift) | Not Started | |
| 3.6 | Implement release sequence | Not Started | |
| 3.7 | Add grasp success detection (force feedback) | Not Started | |

#### Validation Criteria
- [ ] Gripper opens/closes on command
- [ ] Can grasp 3cm cube reliably (>90% success)
- [ ] Grasp force doesn't damage objects
- [ ] Can detect failed grasps

#### Deliverables
- `gripper_controller_node.py` - ROS2 node for gripper
- `GripperCommand.srv` - Service definition
- Grasp parameter configurations

---

### Phase 4: Motion Planning & Execution
**Goal:** Plan and execute collision-free paths for pick and place

#### Requirements
- [ ] Working IK solver
- [ ] Path planning (joint space or Cartesian)
- [ ] Collision avoidance (optional but recommended)
- [ ] Smooth trajectory execution

#### Tasks
| Task | Description | Status | Notes |
|------|-------------|--------|-------|
| 4.1 | Verify IK solver works for target poses | Partial | piper_ik_node.py exists |
| 4.2 | Implement Cartesian path planning | Not Started | |
| 4.3 | Add workspace boundary limits | Not Started | |
| 4.4 | Implement trajectory interpolation | Not Started | |
| 4.5 | Add velocity/acceleration limits | Not Started | |
| 4.6 | Test motion smoothness | Not Started | |
| 4.7 | Add collision checking (optional) | Not Started | |

#### Validation Criteria
- [ ] Arm reaches target poses accurately (<1cm error)
- [ ] Motion is smooth (no jerky movements)
- [ ] Arm stays within safe workspace
- [ ] No self-collisions

#### Deliverables
- `motion_planner_node.py` - ROS2 node for planning
- `ExecuteTrajectory.action` - Action definition
- Workspace configuration file

---

### Phase 5: Pick and Place Pipeline
**Goal:** Complete autonomous pick and place operation

#### Requirements
- [ ] All previous phases working
- [ ] State machine for pick-place sequence
- [ ] Error handling and recovery

#### Tasks
| Task | Description | Status | Notes |
|------|-------------|--------|-------|
| 5.1 | Define pick and place state machine | Not Started | |
| 5.2 | Implement "detect object" state | Not Started | |
| 5.3 | Implement "move to pre-grasp" state | Not Started | |
| 5.4 | Implement "approach and grasp" state | Not Started | |
| 5.5 | Implement "lift object" state | Not Started | |
| 5.6 | Implement "move to place location" state | Not Started | |
| 5.7 | Implement "release object" state | Not Started | |
| 5.8 | Implement "return home" state | Not Started | |
| 5.9 | Add error handling and retry logic | Not Started | |
| 5.10 | Test full pipeline | Not Started | |

#### Validation Criteria
- [ ] Successfully picks object from random position
- [ ] Places object at designated location
- [ ] Success rate >80% over 20 trials
- [ ] Handles "object not found" gracefully
- [ ] Handles "grasp failed" with retry

#### Deliverables
- `pick_place_node.py` - Main pick and place node
- `pick_place.launch.py` - Launch file for full system
- Demo video of working system

---

### Phase 6: Color Sorting Application
**Goal:** Sort objects by color into designated bins

#### Requirements
- [ ] Pick and place working
- [ ] Color detection working
- [ ] Multiple place locations defined

#### Tasks
| Task | Description | Status | Notes |
|------|-------------|--------|-------|
| 6.1 | Define bin locations for each color | Not Started | |
| 6.2 | Extend detection to identify colors | Not Started | |
| 6.3 | Map color to destination bin | Not Started | |
| 6.4 | Implement sorting loop | Not Started | |
| 6.5 | Add object counting/tracking | Not Started | |
| 6.6 | Test with multiple objects | Not Started | |

#### Validation Criteria
- [ ] Correctly identifies red, green, blue objects
- [ ] Places each color in correct bin
- [ ] Sorting accuracy >90%
- [ ] Can sort 10+ objects in sequence

#### Deliverables
- `color_sorter_node.py` - Sorting application
- Configuration for bin locations
- Demo video of color sorting

---

### Phase 7: Voice Control Integration
**Goal:** Control the arm with voice commands

#### Requirements
- [ ] Microphone input
- [ ] Speech recognition library
- [ ] Command parsing
- [ ] Action triggering

#### Tasks
| Task | Description | Status | Notes |
|------|-------------|--------|-------|
| 7.1 | Set up microphone input | Not Started | |
| 7.2 | Implement speech recognition | Not Started | Use Python speech_recognition |
| 7.3 | Define command vocabulary | Not Started | |
| 7.4 | Implement command parser | Not Started | |
| 7.5 | Map commands to robot actions | Not Started | |
| 7.6 | Add wake word detection (optional) | Not Started | |
| 7.7 | Test voice commands | Not Started | |

#### Command Vocabulary (Proposed)
| Voice Command | Action |
|---------------|--------|
| "Pick up [color] object" | Find and pick specified object |
| "Place object" | Place currently held object |
| "Sort objects" | Start sorting routine |
| "Go home" | Return to home position |
| "Stop" | Emergency stop |
| "Open gripper" | Open gripper |
| "Close gripper" | Close gripper |

#### Validation Criteria
- [ ] Recognizes commands in quiet environment >90%
- [ ] Correct action triggered for each command
- [ ] Response time < 2 seconds
- [ ] "Stop" command works immediately

#### Deliverables
- `voice_control_node.py` - Voice control node
- Command configuration file
- Demo video with voice control

---

### Phase 8: System Integration & Demo
**Goal:** Fully integrated system with all features working together

#### Requirements
- [ ] All previous phases complete
- [ ] Unified launch system
- [ ] Documentation

#### Tasks
| Task | Description | Status | Notes |
|------|-------------|--------|-------|
| 8.1 | Create master launch file | Not Started | |
| 8.2 | Add system health monitoring | Not Started | |
| 8.3 | Create user documentation | Not Started | |
| 8.4 | Record demo videos | Not Started | |
| 8.5 | Performance optimization | Not Started | |
| 8.6 | Final testing and validation | Not Started | |

#### Validation Criteria
- [ ] System starts with single launch command
- [ ] All features work together
- [ ] Can run full demo without manual intervention
- [ ] Documentation is complete and accurate

#### Deliverables
- `armpi_replication.launch.py` - Master launch file
- `USER_GUIDE.md` - Complete user documentation
- Demo videos for all features
- Final project report

---

## Progress Tracking

### Overall Progress
| Phase | Status | Completion % |
|-------|--------|--------------|
| Phase 1: Calibration | In Progress | 60% |
| Phase 2: Detection | Not Started | 0% |
| Phase 3: Gripper | Not Started | 0% |
| Phase 4: Motion | Partial | 20% |
| Phase 5: Pick & Place | Not Started | 0% |
| Phase 6: Color Sorting | Not Started | 0% |
| Phase 7: Voice Control | Not Started | 0% |
| Phase 8: Integration | Not Started | 0% |

**Overall Project Completion: ~5%**

### Milestones
| Milestone | Target Date | Status |
|-----------|-------------|--------|
| Camera-arm calibration complete | TBD | Not Started |
| First successful autonomous pick | TBD | Not Started |
| Color sorting demo working | TBD | Not Started |
| Voice control working | TBD | Not Started |
| Full system demo | TBD | Not Started |

---

## Technical Specifications

### Hardware
- **Arm:** Piper 6-DOF, CAN bus control at 1Mbps
- **Camera:** Intel RealSense (RGB 1920x1080, Depth 1280x720)
- **Gripper:** Piper integrated gripper, 0-70mm range
- **Computer:** Jetson/Ubuntu with ROS2 Jazzy

### Software Stack
- ROS2 Jazzy
- Python 3.12
- OpenCV for vision
- piper_sdk for arm control
- pyrealsense2 for camera

### Communication
- `/joint_states` - Joint positions (sensor_msgs/JointState)
- `/target_pose` - Target end-effector pose (geometry_msgs/PoseStamped)
- `/detected_objects` - Detected objects (custom message)
- `/gripper_command` - Gripper commands (custom service)
- `/voice_command` - Voice commands (std_msgs/String)

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Camera calibration inaccurate | High | Medium | Use multiple calibration methods, validate thoroughly |
| IK solver fails for some poses | Medium | Medium | Add workspace limits, use multiple IK seeds |
| Gripper drops objects | High | Medium | Tune grip force, add grasp verification |
| Lighting affects detection | Medium | High | Use depth for localization, add lighting normalization |
| Voice recognition unreliable | Low | Medium | Use push-to-talk, add confirmation |

---

## Notes & Decisions Log

| Date | Note |
|------|------|
| 2026-01-21 | Project plan created. Existing sim-to-real bridge working. |
| | |
| | |

---

## References

- ArmPi Ultra package: `/home/robotics_urop/Documents/Robotic AI/Robotic-AI/ArmPi Ultra-20260121T171349Z-3-003/`
- Piper SDK: `/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper_sdk/`
- Existing detection code: `/home/robotics_urop/Documents/Robotic AI/Robotic-AI/piper/cubeAndLineDet/`
- Sim-to-real guide: `/home/robotics_urop/Documents/Robotic AI/Robotic-AI/SIM_TO_REAL_GUIDE.md`
