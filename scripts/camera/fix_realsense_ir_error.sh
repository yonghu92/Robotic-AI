#!/bin/bash
# Fix RealSense IR Stream Error

echo "=========================================="
echo "Fixing RealSense IR Stream Error"
echo "=========================================="

# Check if camera is busy
echo "1. Checking camera status..."
rs-enumerate-devices 2>/dev/null || {
    echo "   Installing RealSense tools..."
    sudo apt install -y librealsense2-utils
}

echo ""
echo "2. Stopping any running RealSense nodes..."
pkill -f realsense2_camera_node || true
sleep 2

echo ""
echo "3. Resetting USB device..."
# Find RealSense device
DEVICE=$(lsusb | grep -i "Intel.*RealSense" | head -1 | awk '{print $6}' | tr ':' ' ')
if [ -n "$DEVICE" ]; then
    echo "   Found device: $DEVICE"
    sudo usb_modeswitch -v ${DEVICE% *} -p ${DEVICE#* } -R 2>/dev/null || true
else
    echo "   Device not found via lsusb, trying direct reset..."
fi

# Alternative: reset via sysfs
for usb_dev in /sys/bus/usb/devices/*/idVendor; do
    if [ -f "$usb_dev" ]; then
        vendor=$(cat "$usb_dev" 2>/dev/null)
        if [ "$vendor" = "8086" ]; then  # Intel vendor ID
            device_path=$(dirname "$usb_dev")
            echo "   Resetting USB device at $device_path"
            echo 0 | sudo tee "$device_path/authorized" > /dev/null 2>&1
            sleep 1
            echo 1 | sudo tee "$device_path/authorized" > /dev/null 2>&1
            sleep 2
        fi
    fi
done

echo ""
echo "4. Checking camera firmware..."
rs-enumerate-devices -c 2>/dev/null | grep -A 5 "Device" || echo "   Run: rs-enumerate-devices -c to see details"

echo ""
echo "=========================================="
echo "Solutions to try:"
echo "=========================================="
echo ""
echo "A. USB Port Issue:"
echo "   - Unplug camera and plug into a USB 3.0 port (usually blue)"
echo "   - Check: lsusb -t (should show '480M' for USB 3.0)"
echo ""
echo "B. IR Stream Error:"
echo "   - Try disabling IR stream in launch file:"
echo "     ros2 launch realsense2_camera rs_launch.py enable_infra:=false"
echo ""
echo "   - Or use depth-only mode:"
echo "     ros2 launch realsense2_camera rs_launch.py enable_color:=false enable_infra:=false"
echo ""
echo "C. Update Firmware:"
echo "   - Download Intel RealSense Firmware Update Tool"
echo "   - https://dev.intelrealsense.com/docs/firmware-update-tool"
echo ""
echo "D. Check Camera Health:"
echo "   rs-enumerate-devices -c"
echo ""
