#!/bin/bash
# Script to configure CAN interface can0 with 1Mbps bitrate

echo "Bringing down can0..."
sudo ip link set can0 down

echo "Configuring can0 with 1000000 bitrate..."
sudo ip link set can0 type can bitrate 1000000

echo "Bringing can0 back up..."
sudo ip link set can0 up

echo "Verifying configuration..."
ip link show can0

echo "Done!"
