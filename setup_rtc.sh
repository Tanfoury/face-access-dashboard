#!/bin/bash
# setup_rtc.sh - DS1307 RTC Setup Script for Raspberry Pi

echo "=================================================="
echo "DS1307 RTC Setup for Raspberry Pi"
echo "=================================================="

# Check if running on Raspberry Pi
if ! grep -q "BCM" /proc/device-tree/model 2>/dev/null; then
    echo "Warning: This script is designed for Raspberry Pi"
fi

# Update system
echo "[1/5] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
echo "[2/5] Installing required packages..."
sudo apt-get install -y python3-smbus i2c-tools

# Install Python packages
echo "[3/5] Installing Python packages..."
pip install smbus2

# Enable I2C interface
echo "[4/5] Enabling I2C interface..."
sudo raspi-config nonint do_i2c 0

# Scan I2C bus to detect DS1307
echo "[5/5] Scanning I2C bus for DS1307 device..."
echo ""
echo "Detected I2C devices:"
i2cdetect -y 1

echo ""
echo "=================================================="
echo "Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. If you see '68' in the I2C scan above, your DS1307 is connected correctly"
echo "2. Run the RTC initialization in your Python code"
echo "3. The RTC module will automatically sync system time on startup"
echo ""
echo "To manually test the RTC, run:"
echo "  python3 -c \"from rtc import initialize_rtc; r = initialize_rtc(); print(r.read_time())\""
