cmake_minimum_required(VERSION 3.10)
project(cubeAndLineDet)

## Compile as C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_compile_options(-std=c++17)
add_definitions(-DAPI_EXPORTS)
set(CMAKE_BUILD_TYPE Debug)

set(PCL_DIR "/usr/local/share/pcl-1.10")

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(image_transport REQUIRED)
find_package(visualization_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(pcl_conversions REQUIRED)
find_package(PCL 1.10 REQUIRED COMPONENTS common io surface visualization)
find_package(OpenCV REQUIRED)
find_package(Eigen3 REQUIRED)

include_directories(
  include
  ${OpenCV_INCLUDE_DIRS}
  ${PCL_INCLUDE_DIRS}
  /usr/local/include/pcl-1.10
  ${EIGEN3_INCLUDE_DIR}
)

# Include cv_bridge headers - ament_target_dependencies should handle this, but add explicit include if needed
if(cv_bridge_FOUND)
  include_directories(${cv_bridge_INCLUDE_DIRS})
  # Also try common ROS 2 locations
  include_directories(/opt/ros/jazzy/include)
endif()

# Add executables
add_executable(cube_det src/cube_det.cpp)
ament_target_dependencies(cube_det
  rclcpp
  sensor_msgs
  cv_bridge
  image_transport
  visualization_msgs
  geometry_msgs
  std_msgs
)

target_link_libraries(cube_det
  ${OpenCV_LIBRARIES}
  ${PCL_LIBRARIES}
  ${VTK_LIBRARIES}
  pcl_surface
)

add_executable(line_det src/line_det.cpp)
ament_target_dependencies(line_det
  rclcpp
  sensor_msgs
  cv_bridge
  image_transport
  visualization_msgs
  geometry_msgs
  std_msgs
  pcl_conversions
)

target_link_libraries(line_det
  ${OpenCV_LIBRARIES}
  ${PCL_LIBRARIES}
  ${VTK_LIBRARIES}
  pcl_surface
)

# Install targets
install(TARGETS cube_det line_det
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
