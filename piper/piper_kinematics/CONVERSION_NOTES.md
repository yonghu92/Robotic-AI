# ROS1 to ROS2 Conversion Notes

## What Was Converted

### ✅ Completed:
1. **Python Script** (`scripts/interactive_pose_marker.py`)
   - Converted from `rospy` to `rclpy`
   - Updated parameter handling
   - Updated TF broadcasting to use `tf2_ros`
   - Updated time handling

2. **package.xml**
   - Converted from `catkin` to `ament_cmake` format
   - Updated dependencies to ROS2 packages
   - Note: `piper_msgs` dependency commented out (needs separate conversion)

3. **CMakeLists.txt**
   - Converted from `catkin` to `ament_cmake`
   - C++ executables commented out (need ROS2 conversion)

4. **Launch File**
   - Converted from XML (`piper_ik.launch`) to Python (`piper_ik.launch.py`)
   - C++ node commented out until conversion is complete

### ⚠️ Still Needs Work:

1. **C++ Nodes** (`src/piper_ik_node.cpp`, `src/piper_ik_node_use_yaik.cpp`)
   - Need conversion from ROS1 to ROS2:
     - `ros::NodeHandle` → `rclcpp::Node`
     - `ros::Publisher` → `rclcpp::Publisher`
     - `ros::Subscriber` → `rclcpp::Subscription`
     - `ros::Timer` → `rclcpp::Timer`
     - `tf::TransformBroadcaster` → `tf2_ros::TransformBroadcaster`
     - Message types may need updates

2. **piper_msgs Package**
   - Custom message package needs ROS2 conversion
   - Currently commented out in dependencies

3. **Interactive Markers**
   - Need to verify `interactive_markers` package is available in ROS2
   - May need to install: `ros-jazzy-interactive-markers`

## How to Build and Run

### 1. Install Dependencies

```bash
# Install ROS2 interactive markers (if available)
sudo apt install -y ros-jazzy-interactive-markers

# Install Eigen3
sudo apt install -y libeigen3-dev

# Install other ROS2 packages
sudo apt install -y \
    ros-jazzy-visualization-msgs \
    ros-jazzy-geometry-msgs \
    ros-jazzy-sensor-msgs \
    ros-jazzy-tf2-ros \
    ros-jazzy-tf2-geometry-msgs
```

### 2. Build the Package

```bash
# Make sure ROS2 is sourced
source /opt/ros/jazzy/setup.bash

# Create workspace if needed
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src

# Copy or symlink the package
cp -r ~/Documents/Robotic\ AI/Robotic-AI/piper/piper_kinematics ~/ros2_ws/src/

# Fix package.xml if needed
sed -i 's/<n>/<name>/g; s/<\/n>/<\/name>/g' ~/ros2_ws/src/piper_kinematics/package.xml

# Build
cd ~/ros2_ws
colcon build --packages-select piper_kinematics

# Source workspace
source ~/ros2_ws/install/setup.bash
```

### 3. Run the Python Node

```bash
# Run the interactive pose marker
ros2 run piper_kinematics interactive_pose_marker.py

# Or use the launch file
ros2 launch piper_kinematics piper_ik.launch.py
```

## Known Issues

1. **Interactive Markers in ROS2**
   - The `interactive_markers` package may not be fully available in ROS2 Jazzy
   - May need to use a ROS2-compatible fork or alternative
   - Check: https://github.com/ros2/interactive_markers

2. **C++ Nodes Not Converted**
   - The main IK solver nodes are still in ROS1 format
   - Python script can run independently for testing
   - C++ conversion is more complex and needs careful testing

3. **piper_msgs Dependency**
   - Custom messages need ROS2 conversion
   - May need to create a ROS2 version of the messages package

## Testing

To test the Python node:

```bash
# Terminal 1: Run the node
ros2 run piper_kinematics interactive_pose_marker.py

# Terminal 2: Check topics
ros2 topic list
ros2 topic echo /target_pose

# Terminal 3: Check TF
ros2 run tf2_ros tf2_echo base_link target_pose
```

## Next Steps

1. ✅ Test Python script conversion
2. ⏳ Convert C++ nodes to ROS2
3. ⏳ Convert piper_msgs to ROS2
4. ⏳ Test full functionality with RViz
