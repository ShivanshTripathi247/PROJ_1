import time
import threading
import struct
import smbus2 as smbus
from max30102.max30102 import MAX30102
from max30102.heartrate_monitor import HeartRateMonitor

# I2C bus
bus = smbus.SMBus(1)

# I2C addresses
MPU9250_ADDR = 0x68
AK8963_ADDR = 0x0C

# MPU9250 registers
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
USER_CTRL = 0x6A
INT_PIN_CFG = 0x37

# AK8963 registers
AK8963_CNTL1 = 0x0A
AK8963_ST1 = 0x02
AK8963_XOUT_L = 0x03
AK8963_ST2 = 0x09

class MPU9250_9Axis:
    def __init__(self):
        self.setup_mpu9250()
        self.setup_magnetometer()
        
    def setup_mpu9250(self):
        """Initialize MPU9250"""
        try:
            # Wake up MPU9250
            bus.write_byte_data(MPU9250_ADDR, PWR_MGMT_1, 0x00)
            time.sleep(0.1)
            print("MPU9250 initialized successfully")
            self.mpu_available = True
        except Exception as e:
            print(f"MPU9250 initialization failed: {e}")
            self.mpu_available = False
            
    def setup_magnetometer(self):
        """Enable bypass mode for magnetometer access"""
        try:
            # Disable I2C master mode and enable bypass
            bus.write_byte_data(MPU9250_ADDR, USER_CTRL, 0x00)
            time.sleep(0.01)
            
            # Enable I2C bypass
            bus.write_byte_data(MPU9250_ADDR, INT_PIN_CFG, 0x02)
            time.sleep(0.01)
            
            # Check if AK8963 is accessible
            who_am_i = bus.read_byte_data(AK8963_ADDR, 0x00)  # Should return 0x48
            if who_am_i == 0x48:
                print(f"AK8963 magnetometer found! WHO_AM_I: 0x{who_am_i:02X}")
                
                # Set AK8963 to continuous measurement mode (100Hz)
                bus.write_byte_data(AK8963_ADDR, AK8963_CNTL1, 0x16)
                time.sleep(0.01)
                
                self.mag_available = True
            else:
                print(f"AK8963 not found. WHO_AM_I: 0x{who_am_i:02X}")
                self.mag_available = False
                
        except Exception as e:
            print(f"Magnetometer setup failed: {e}")
            self.mag_available = False
    
    def read_accel_gyro(self):
        """Read accelerometer and gyroscope data"""
        if not self.mpu_available:
            return None
            
        try:
            raw_data = bus.read_i2c_block_data(MPU9250_ADDR, ACCEL_XOUT_H, 14)
            
            # Convert to signed 16-bit values
            accel_x = struct.unpack('>h', bytes(raw_data[0:2]))[0] / 16384.0
            accel_y = struct.unpack('>h', bytes(raw_data[2:4]))[0] / 16384.0
            accel_z = struct.unpack('>h', bytes(raw_data[4:6]))[0] / 16384.0
            
            temp = struct.unpack('>h', bytes(raw_data[6:8]))[0] / 340.0 + 36.53
            
            gyro_x = struct.unpack('>h', bytes(raw_data[8:10]))[0] / 131.0
            gyro_y = struct.unpack('>h', bytes(raw_data[10:12]))[0] / 131.0
            gyro_z = struct.unpack('>h', bytes(raw_data[12:14]))[0] / 131.0
            
            return {
                'accel': {'x': accel_x, 'y': accel_y, 'z': accel_z},
                'gyro': {'x': gyro_x, 'y': gyro_y, 'z': gyro_z},
                'temp': temp
            }
        except Exception as e:
            print(f"IMU read error: {e}")
            return None
    
    def read_magnetometer(self):
        """Read magnetometer data"""
        if not self.mag_available:
            return {'x': None, 'y': None, 'z': None}
            
        try:
            # Check if data is ready
            status = bus.read_byte_data(AK8963_ADDR, AK8963_ST1)
            if status & 0x01:  # Data ready bit
                # Read 6 bytes of magnetometer data
                mag_data = bus.read_i2c_block_data(AK8963_ADDR, AK8963_XOUT_L, 6)
                
                # Convert to signed 16-bit values (little endian for AK8963)
                mag_x = struct.unpack('<h', bytes(mag_data[0:2]))[0] * 0.15
                mag_y = struct.unpack('<h', bytes(mag_data[2:4]))[0] * 0.15  
                mag_z = struct.unpack('<h', bytes(mag_data[4:6]))[0] * 0.15
                
                # Read ST2 to complete measurement
                bus.read_byte_data(AK8963_ADDR, AK8963_ST2)
                
                return {'x': mag_x, 'y': mag_y, 'z': mag_z}
                
        except Exception as e:
            print(f"Magnetometer read error: {e}")
            
        return {'x': None, 'y': None, 'z': None}

# Initialize sensors
mpu9250 = MPU9250_9Axis()

# Initialize MAX30102
spo2_sensor = MAX30102()
hr_monitor = HeartRateMonitor(print_result=False, print_raw=False)
hr_monitor.sensor = spo2_sensor

def read_all_sensors():
    try:
        hr_monitor.start_sensor()
        print("9-Axis MPU9250 + MAX30102 initialized!")
        print("=" * 60)
        
        while True:
            timestamp = time.time()
            
            # Read all 9-axis data
            imu_data = mpu9250.read_accel_gyro()
            mag_data = mpu9250.read_magnetometer()
            
            # Get heart rate and SpO2
            bpm = hr_monitor.bpm if hasattr(hr_monitor, 'bpm') else 0
            spo2 = hr_monitor.spo2 if hasattr(hr_monitor, 'spo2') else None
            
            if imu_data:
                print(f"[{time.strftime('%H:%M:%S', time.localtime(timestamp))}]")
                print(f"Accel: X={imu_data['accel']['x']:.3f}g Y={imu_data['accel']['y']:.3f}g Z={imu_data['accel']['z']:.3f}g")
                print(f"Gyro:  X={imu_data['gyro']['x']:.1f}°/s Y={imu_data['gyro']['y']:.1f}°/s Z={imu_data['gyro']['z']:.1f}°/s")
                
                if mag_data['x'] is not None:
                    print(f"Mag:   X={mag_data['x']:.1f}µT Y={mag_data['y']:.1f}µT Z={mag_data['z']:.1f}µT")
                else:
                    print("Mag:   No data available")
                    
                print(f"Temp:  {imu_data['temp']:.1f}°C")
                print(f"Vitals: {bpm}BPM, SpO2={spo2}%")
                print("-" * 50)
            
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        hr_monitor.sensor.shutdown()
        print("\nStopped by user.")

if __name__ == "__main__":
    read_all_sensors()
