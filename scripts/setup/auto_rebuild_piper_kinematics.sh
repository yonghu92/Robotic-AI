#!/bin/bash
# Auto-rebuild piper_kinematics package continuously without prompts

# Function to rebuild
rebuild() {
    echo "=========================================="
    echo "Rebuilding piper_kinematics..."
    echo "=========================================="
    
    # Kill existing node
    pkill -f piper_ik_node 2>/dev/null
    
    # Build the package
    cd ~/ros2_ws && colcon build --packages-select piper_kinematics 2>&1 | tail -3
    
    return $?
}

# Check if we should run once or continuously
if [ "$1" == "--loop" ] || [ "$1" == "-l" ]; then
    echo "Running in continuous loop mode. Press Ctrl+C to stop."
    echo ""
    
    while true; do
        rebuild
        echo ""
        echo "Waiting 5 seconds before next rebuild..."
        sleep 5
    done
else
    # Run once
    rebuild
    exit $?
fi
