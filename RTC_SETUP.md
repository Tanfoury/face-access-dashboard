# DS1307 RTC Configuration Guide

## Hardware Connection

### DS1307 Pinout
- **VCC** → Raspberry Pi 3.3V (Pin 1 or 17)
- **GND** → Raspberry Pi GND (Pin 6, 9, 14, 20, 25, 30, 34, or 39)
- **SDA** → Raspberry Pi GPIO 2 (Pin 3, I2C data)
- **SCL** → Raspberry Pi GPIO 3 (Pin 5, I2C clock)
- **BAT** → 3V coin cell battery (optional, for backup power)

### Wiring Diagram
```
DS1307 Module          Raspberry Pi
┌─────────────┐       ┌──────────────┐
│  VCC    ────┼───────┼─ 3.3V (Pin1)│
│  GND    ────┼───────┼─ GND (Pin6) │
│  SDA    ────┼───────┼─ GPIO2 (Pin3)│
│  SCL    ────┼───────┼─ GPIO3 (Pin5)│
│  BAT    ────┼─ (Coin Cell Battery) │
└─────────────┘       └──────────────┘
```

## Installation Steps

### 1. Run Setup Script (Automated)
```bash
chmod +x setup_rtc.sh
sudo ./setup_rtc.sh
```

### 2. Manual Setup
```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install I2C tools
sudo apt-get install -y python3-smbus i2c-tools

# Install Python smbus2
pip install smbus2

# Enable I2C (if not already enabled)
sudo raspi-config
# Navigate to: Interface Options → I2C → Yes
```

## Configuration

### Check if DS1307 is Detected
```bash
i2cdetect -y 1
```
You should see `68` in the output, confirming the DS1307 is at I2C address 0x68.

### Python Configuration (config.py)
```python
# RTC Configuration
RTC_ENABLED         = True
RTC_ADDRESS         = 0x68        # DS1307 I2C address
RTC_BUS             = 1           # Raspberry Pi I2C bus
RTC_SYNC_SYSTEM     = True        # Sync system time from RTC on startup
```

## Usage in Python Code

### Read Time from RTC
```python
from rtc import initialize_rtc

rtc = initialize_rtc()
current_time = rtc.read_time()
print(f"RTC Time: {current_time}")
```

### Set RTC Time
```python
from rtc import initialize_rtc
from datetime import datetime

rtc = initialize_rtc()

# Set to current system time
rtc.set_time()

# Set to specific time
rtc.set_time(datetime(2024, 5, 21, 14, 30, 0))
```

### Sync System to RTC
```python
rtc = initialize_rtc()
rtc.sync_system_to_rtc()  # RTC → System time
```

### Sync RTC to System
```python
rtc = initialize_rtc()
rtc.sync_rtc_to_system()  # System time → RTC
```

## Troubleshooting

### I2C Device Not Found
```bash
# Check if I2C is enabled
sudo raspi-config nonint get_i2c

# Enable I2C
sudo raspi-config nonint do_i2c 0

# Restart
sudo reboot
```

### Permission Denied on /dev/i2c-1
```bash
# Add user to i2c group
sudo usermod -aG i2c $USER
sudo usermod -aG gpio $USER

# Log out and back in
exit
```

### Module Not Working
```python
# Test import
python3 -c "import smbus2; print('smbus2 OK')"

# Test RTC detection
python3 -c "from rtc import DS1307RTC; r = DS1307RTC(); print(r.enabled)"
```

### Time Still Wrong After Sync
- Check if battery is installed and working (optional but recommended)
- Verify I2C connection using `i2cdetect -y 1`
- Test with `python3 test_rtc.py` (see test file)

## Main3.py Integration

The RTC is automatically initialized when `main3.py` starts:

```python
def run():
    init_db()
    daily_reset()
    lcd_init()
    rtc_init()  # ← RTC initialized here
    # ... rest of initialization
```

- If `RTC_SYNC_SYSTEM = True`, system time will sync from RTC on startup
- RTC is used for all access log timestamps
- Battery-backed time is preserved across power failures

## Files Modified
- `config.py` - Added RTC configuration parameters
- `main3.py` - Added RTC import and initialization
- `rtc.py` - New RTC driver module
- `setup_rtc.sh` - RTC setup script

## API Reference

### DS1307RTC Class
```python
class DS1307RTC:
    __init__(i2c_address=0x68, i2c_bus=1)
    read_time() → datetime
    set_time(dt=None) → bool
    sync_system_to_rtc() → bool
    sync_rtc_to_system() → bool
    enable_oscillator() → bool
    disable_oscillator() → bool
    close() → None
```

## References
- DS1307 Datasheet: https://datasheets.maximintegrated.com/en/ds/DS1307.pdf
- RPi I2C: https://www.raspberrypi.com/documentation/computers/configuration.html#i2c
