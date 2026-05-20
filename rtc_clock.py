# rtc_clock.py
# Lecture RTC DS1307 via /dev/rtc0 (kernel driver)

import struct, fcntl, os
from datetime import datetime
from config import DEVICE

RTC_RD_TIME = 0x80247009

def get_datetime() -> datetime:
    if DEVICE != "PI":
        return datetime.now()
    try:
        with open('/dev/rtc0', 'rb') as f:
            buf = fcntl.ioctl(f, RTC_RD_TIME, b'\x00' * 36)
        t = struct.unpack('9i', buf[:36])
        # t = (sec, min, hour, mday, mon, year, wday, yday, isdst)
        return datetime(t[5] + 1900, t[4] + 1, t[3], t[2], t[1], t[0])
    except Exception as e:
        print(f"[RTC] Erreur lecture : {e}")
        return datetime.now()

def get_time_str() -> str:
    return get_datetime().strftime("%H:%M")

def get_datetime_str() -> str:
    return get_datetime().strftime("%d/%m/%Y %H:%M")
