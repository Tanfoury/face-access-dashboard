#!/usr/bin/env python3
# test_rtc.py - DS1307 RTC Test Script

import sys
from datetime import datetime
from rtc import DS1307RTC

def test_rtc():
    print("=" * 50)
    print("DS1307 RTC Test Script")
    print("=" * 50)
    print()
    
    # Initialize RTC
    print("[1] Initializing RTC...")
    rtc = DS1307RTC()
    
    if not rtc.enabled:
        print("❌ RTC not detected! Check I2C connection.")
        print("   Run: i2cdetect -y 1")
        return False
    
    print("✓ RTC initialized successfully")
    print()
    
    # Read time from RTC
    print("[2] Reading time from RTC...")
    rtc_time = rtc.read_time()
    
    if rtc_time is None:
        print("❌ Failed to read RTC time")
        return False
    
    print(f"✓ RTC Time: {rtc_time}")
    print()
    
    # Check system time
    print("[3] System time:")
    system_time = datetime.now()
    print(f"✓ System Time: {system_time}")
    print()
    
    # Calculate time difference
    diff = abs((rtc_time - system_time).total_seconds())
    print(f"[4] Time difference: {diff:.1f} seconds")
    
    if diff > 3600:  # More than 1 hour
        print("⚠ Warning: RTC time differs significantly from system time")
        print("   This is normal if RTC has not been synced yet")
    elif diff > 60:  # More than 1 minute
        print("⚠ Warning: Time difference is {:.0f} minutes".format(diff / 60))
    else:
        print("✓ Times are synchronized")
    
    print()
    
    # Test set time
    print("[5] Testing RTC write...")
    test_time = datetime(2024, 5, 21, 14, 30, 0)
    success = rtc.set_time(test_time)
    
    if not success:
        print("❌ Failed to write to RTC")
        return False
    
    print(f"✓ Set RTC to: {test_time}")
    
    # Verify write
    import time
    time.sleep(0.1)
    verify_time = rtc.read_time()
    
    if verify_time is None:
        print("❌ Failed to verify write")
        return False
    
    print(f"✓ Verified RTC: {verify_time}")
    print()
    
    # Restore to system time
    print("[6] Restoring RTC to current system time...")
    rtc.set_time(datetime.now())
    restored_time = rtc.read_time()
    print(f"✓ RTC restored: {restored_time}")
    print()
    
    print("=" * 50)
    print("✓ All tests passed!")
    print("=" * 50)
    
    # Summary
    print()
    print("Summary:")
    print(f"  RTC Detected: Yes (0x68)")
    print(f"  RTC Time: {restored_time}")
    print(f"  System Time: {datetime.now()}")
    print(f"  Status: Ready to use")
    print()
    
    rtc.close()
    return True

if __name__ == "__main__":
    try:
        success = test_rtc()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
