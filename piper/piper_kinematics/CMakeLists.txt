cmake_minimum_required(VERSION 3.10)
project(piper_kinematics)

## Compile as C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_compile_options(-std=c++17)
add_definitions(-DAPI_EXPORTS)
set(CMAKE_BUILD_TYPE Release)

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclpy REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(visualization_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(interactive_markers REQUIRED)
find_package(Eigen3 REQUIRED)

# Include directories
include_directories(
  include
  ${EIGEN3_INCLUDE_DIR}
)

# Add C++ executables (Note: C++ code needs ROS2 conversion)
# Uncomment and convert C++ code when ready
# add_executable(piper_ik_node src/piper_ik_node.cpp)
# ament_target_dependencies(piper_ik_node
#   rclcpp
#   sensor_msgs
#   geometry_msgs
#   visualization_msgs
#   tf2_ros
#   tf2_geometry_msgs
# )
# target_link_libraries(piper_ik_node
#   ${EIGEN3_LIBRARIES}
# )

# Install Python scripts
install(PROGRAMS
  scripts/interactive_pose_marker.py
  scripts/piper_ik_node.py
  DESTINATION lib/${PROJECT_NAME}
)

# Install launch files
install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

# Install C++ executables (when converted)
# install(TARGETS piper_ik_node
#   DESTINATION lib/${PROJECT_NAME}
# )

ament_package()
