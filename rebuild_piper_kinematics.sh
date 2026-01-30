#!/bin/bash
# Auto-rebuild piper_kinematics package without prompts

# Kill existing node
pkill -f piper_ik_node 2>/dev/null

# Build the package
cd ~/ros2_ws && colcon build --packages-select piper_kinematics 2>&1 | tail -3

# Exit with the build result
exit $?
