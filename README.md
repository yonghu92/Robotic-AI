# Piper Arm Robotics Project

> **Branch: `anika-rgi-gripper-integration`** - RGI Gripper Integration & Control Systems

## Quick Navigation

| Feature | Location | Description |
|---------|----------|-------------|
| **Main Control** | [`rgi_gripper/play_and_adjust.py`](rgi_gripper/play_and_adjust.py) | Trajectory recording, playback, gamepad control |
| **Web Interface** | [`rgi_gripper/web_controller.py`](rgi_gripper/web_controller.py) | Remote control with live camera |
| **Training Data** | [`training_data_samples/`](training_data_samples/) | Pick-and-place demo images & GIF |
| **Documentation** | [`docs/`](docs/) | Setup guides, troubleshooting |
| **Camera Scripts** | [`scripts/camera/`](scripts/camera/) | RealSense utilities |
| **Project Summary** | [`PROJECT_MONTHLY_SUMMARY.pdf`](PROJECT_MONTHLY_SUMMARY.pdf) | Full month overview |

## Quick Start

```bash
# Setup CAN
sudo ip link set can0 up type can bitrate 1000000

# Run main control
cd rgi_gripper && python3 play_and_adjust.py

# Or web control
python3 web_controller.py  # Open http://localhost:5000
```

## Project Structure

```
├── rgi_gripper/          # Main control scripts
├── piper/                # Arm components (calibration, gamepad, manipulation)
├── training_data_samples/# Demo training data
├── docs/                 # All documentation
└── scripts/              # Utility scripts (setup, camera, CAN debug)
```

## Demo

![Pick and Place Demo](training_data_samples/pick_and_place_demo.gif)

---

# 松灵学院开源技术贴

**一站式代码仓库**

松灵学院面向所有开发者、高校团队与爱好者，持续发布基于松灵机器人全线产品的**开源示例与教程**。无论你是初次接触，还是想快速落地项目，都能在这里找到“拿即可用”的代码与步骤说明。更多产品DEMO示例将陆续上线，欢迎 Star、提 Issue 或一起共建。

当前聚焦：Piper 系列机械臂

| 标题                                                         | 描述                                            |
| ------------------------------------------------------------ | ----------------------------------------------- |
| [固定点位录制与播放](https://github.com/agilexrobotics/Agilex-College/tree/master/piper/recordAndPlayPos) | 使用Piper录制固定点位运动并播放                 |
| [连续轨迹录制与播放](https://github.com/agilexrobotics/Agilex-College/tree/master/piper/recordAndPlayTraj) | 使用Piepr录制连续运动的轨迹并播放               |
| [机械臂识别方块与曲线](https://github.com/agilexrobotics/Agilex-College/tree/master/piper/cubeAndLineDet) | 使用相机识别方块和曲线；并使Piper机械臂跟随曲线 |
| [手机陀螺仪遥操机械臂](https://github.com/agilexrobotics/Agilex-College/tree/master/piper/mobilePhoneCtl) | 使用手机陀螺仪遥操机械臂臂                      |
| [手势遥操机械臂](https://github.com/agilexrobotics/Agilex-College/tree/master/piper/handpose_det) | 使用手势遥操作Piper机械臂末端六自由度位姿       |
| [Piper_kinematics](https://github.com/agilexrobotics/Agilex-College/tree/master/piper/piper_kinematics) | 机械臂逆解数值教学与Piper底层解析解的调用       |
| [游戏手柄](https://github.com/agilexrobotics/Agilex-College/tree/master/piper/gamepad) | 使用游戏手柄遥操机械臂                          |
| [手眼标定](https://github.com/agilexrobotics/Agilex-College/tree/master/piper/handeye) | Piper手眼标定教程                               |
| [GraspGen](https://github.com/agilexrobotics/Agilex-College/tree/master/piper/GraspGen) | 位姿生成与抓取                                  |
| [Piper_rl](https://github.com/vanstrong12138/Piper_rl.git)   | PiPER强化学习demo                               |
| [Isaac sim 导入piper](https://github.com/agilexrobotics/Agilex-College/tree/master/isaac_sim/piper_isaac_sim) | 在Isaac sim 中导入piper并添加摄像头             |
| [复现RDA_planner](https://github.com/agilexrobotics/Agilex-College/tree/master/limo/RDA_planner) | 复现RDA_planner                                 |



更多内容欢迎关注松灵机器人

网站：https://global.agilex.ai/

微信公众号：松灵机器人

------

**声明**

本仓库内所有内容均为松灵机器人合法拥有，仅限个人学习、研究使用，超出上述范围的使用（包括但不限于基于商业用途的复制、修改、在发布衍生开发等）均需事先获得松灵机器人的书面授权；对于未经授权使用本公司相关作品的行为，本公司将依法追究其法律责任。

如需授权请联系 [support@agilex.ai](https://github.com/agilexrobotics/Agilex-College/blob/master)

