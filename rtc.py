# rtc.py - DS1307 Real-Time Clock Module
import os
import time
import subprocess
from datetime import datetime

class DS1307RTC:
    """DS1307 RTC module - communicates via I2C at address 0x68"""
    
    def __init__(self, i2c_address=0x68, i2c_bus=1):
        """
        Initialize DS1307 RTC
        
        Args:
            i2c_address: I2C address of DS1307 (default 0x68)
            i2c_bus: I2C bus number (1 for Raspberry Pi)
        """
        self.address = i2c_address
        self.bus = i2c_bus
        self.enabled = False
        
        try:
            import smbus2
            self.bus_obj = smbus2.SMBus(self.bus)
            self.enabled = True
            print(f"[RTC] DS1307 initialized on I2C bus {self.bus} at address 0x{self.address:02x}")
        except ImportError:
            print("[RTC] Warning: smbus2 not available. RTC disabled.")
            self.enabled = False
        except Exception as e:
            print(f"[RTC] Error initializing RTC: {e}")
            self.enabled = False
    
    def bcd_to_decimal(self, bcd):
        """Convert BCD (Binary-Coded Decimal) to decimal"""
        return (bcd >> 4) * 10 + (bcd & 0x0F)
    
    def decimal_to_bcd(self, decimal):
        """Convert decimal to BCD"""
        return ((decimal // 10) << 4) + (decimal % 10)
    
    def read_time(self):
        """
        Read current time from DS1307
        
        Returns:
            datetime object or None if read fails
        """
        if not self.enabled:
            return None
        
        try:
            import smbus2
            # DS1307 time registers start at address 0x00
            # Registers: 0x00=seconds, 0x01=minutes, 0x02=hours, 
            #            0x03=day, 0x04=date, 0x05=month, 0x06=year
            data = self.bus_obj.read_i2c_block_data(self.address, 0x00, 7)
            
            seconds = self.bcd_to_decimal(data[0] & 0x7F)  # Mask CH bit
            minutes = self.bcd_to_decimal(data[1])
            hours = self.bcd_to_decimal(data[2] & 0x3F)    # 24-hour format
            day = data[3]  # Day of week (1-7)
            date = self.bcd_to_decimal(data[4])
            month = self.bcd_to_decimal(data[5])
            year = self.bcd_to_decimal(data[6]) + 2000
            
            return datetime(year, month, date, hours, minutes, seconds)
        
        except Exception as e:
            print(f"[RTC] Error reading time: {e}")
            return None
    
    def set_time(self, dt=None):
        """
        Set DS1307 time
        
        Args:
            dt: datetime object (uses current system time if None)
        """
        if not self.enabled:
            return False
        
        if dt is None:
            dt = datetime.now()
        
        try:
            import smbus2
            
            seconds = self.decimal_to_bcd(dt.second)
            minutes = self.decimal_to_bcd(dt.minute)
            hours = self.decimal_to_bcd(dt.hour)
            date = self.decimal_to_bcd(dt.day)
            month = self.decimal_to_bcd(dt.month)
            year = self.decimal_to_bcd(dt.year - 2000)
            
            # Write to DS1307 registers
            self.bus_obj.write_byte_data(self.address, 0x00, seconds)
            self.bus_obj.write_byte_data(self.address, 0x01, minutes)
            self.bus_obj.write_byte_data(self.address, 0x02, hours)
            self.bus_obj.write_byte_data(self.address, 0x04, date)
            self.bus_obj.write_byte_data(self.address, 0x05, month)
            self.bus_obj.write_byte_data(self.address, 0x06, year)
            
            print(f"[RTC] Time set to: {dt}")
            return True
        
        except Exception as e:
            print(f"[RTC] Error setting time: {e}")
            return False
    
    def sync_system_to_rtc(self):
        """Sync system time FROM RTC (RTC -> System)"""
        if not self.enabled:
            return False
        
        rtc_time = self.read_time()
        if rtc_time is None:
            return False
        
        try:
            # Set system time from RTC
            timestamp = int(rtc_time.timestamp())
            os.system(f"sudo date -s @{timestamp}")
            print(f"[RTC] System time synced from RTC: {rtc_time}")
            return True
        except Exception as e:
            print(f"[RTC] Error syncing system to RTC: {e}")
            return False
    
    def sync_rtc_to_system(self):
        """Sync RTC time FROM system (System -> RTC)"""
        if not self.enabled:
            return False
        
        try:
            self.set_time(datetime.now())
            print(f"[RTC] RTC synced from system time: {datetime.now()}")
            return True
        except Exception as e:
            print(f"[RTC] Error syncing RTC to system: {e}")
            return False
    
    def enable_oscillator(self):
        """Enable RTC oscillator (CH bit must be 0)"""
        if not self.enabled:
            return False
        
        try:
            import smbus2
            data = self.bus_obj.read_byte_data(self.address, 0x00)
            # Clear bit 7 (CH) to enable oscillator
            data = data & 0x7F
            self.bus_obj.write_byte_data(self.address, 0x00, data)
            print("[RTC] Oscillator enabled")
            return True
        except Exception as e:
            print(f"[RTC] Error enabling oscillator: {e}")
            return False
    
    def disable_oscillator(self):
        """Disable RTC oscillator (CH bit = 1)"""
        if not self.enabled:
            return False
        
        try:
            import smbus2
            data = self.bus_obj.read_byte_data(self.address, 0x00)
            # Set bit 7 (CH) to disable oscillator
            data = data | 0x80
            self.bus_obj.write_byte_data(self.address, 0x00, data)
            print("[RTC] Oscillator disabled")
            return True
        except Exception as e:
            print(f"[RTC] Error disabling oscillator: {e}")
            return False
    
    def close(self):
        """Close I2C connection"""
        try:
            if self.enabled and hasattr(self, 'bus_obj'):
                self.bus_obj.close()
                print("[RTC] I2C connection closed")
        except Exception as e:
            print(f"[RTC] Error closing RTC: {e}")


# Global RTC instance
_rtc = None

def initialize_rtc():
    """Initialize RTC module"""
    global _rtc
    if _rtc is None:
        _rtc = DS1307RTC()
    return _rtc

def get_rtc():
    """Get RTC instance"""
    global _rtc
    if _rtc is None:
        _rtc = initialize_rtc()
    return _rtc
