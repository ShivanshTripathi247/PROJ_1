import time
import csv
import struct
import smbus2 as smbus
from datetime import datetime
from max30102.max30102 import MAX30102
from max30102.heartrate_monitor import HeartRateMonitor

# I2C bus and addresses
bus = smbus.SMBus(1)
MPU9250_ADDR = 0x68

# MPU9250 registers (6-axis only)
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B

class IMU6Axis:
    def __init__(self):
        self.setup_mpu()
        
    def setup_mpu(self):
        """Initialize MPU9250 for 6-axis readings only"""
        try:
            bus.write_byte_data(MPU9250_ADDR, PWR_MGMT_1, 0x00)
            time.sleep(0.1)
            print("✅ 6-axis IMU initialized successfully")
            self.available = True
        except Exception as e:
            print(f"❌ IMU initialization failed: {e}")
            self.available = False
    
    def read_data(self):
        """Read accelerometer and gyroscope data"""
        if not self.available:
            return None
            
        try:
            raw_data = bus.read_i2c_block_data(MPU9250_ADDR, ACCEL_XOUT_H, 14)
            
            # Accelerometer (±2g range)
            ax = struct.unpack('>h', bytes(raw_data[0:2]))[0] / 16384.0
            ay = struct.unpack('>h', bytes(raw_data[2:4]))[0] / 16384.0
            az = struct.unpack('>h', bytes(raw_data[4:6]))[0] / 16384.0
            
            # Temperature
            temp = struct.unpack('>h', bytes(raw_data[6:8]))[0] / 340.0 + 36.53
            
            # Gyroscope (±250°/s range)
            gx = struct.unpack('>h', bytes(raw_data[8:10]))[0] / 131.0
            gy = struct.unpack('>h', bytes(raw_data[10:12]))[0] / 131.0
            gz = struct.unpack('>h', bytes(raw_data[12:14]))[0] / 131.0
            
            return {
                'ax': round(ax, 4), 'ay': round(ay, 4), 'az': round(az, 4),
                'gx': round(gx, 4), 'gy': round(gy, 4), 'gz': round(gz, 4),
                'temp': round(temp, 2)
            }
            
        except Exception as e:
            print(f"❌ IMU read error: {e}")
            return None

# Initialize sensors
print("Initializing sensors...")
imu = IMU6Axis()
spo2_sensor = MAX30102()
hr_monitor = HeartRateMonitor(print_result=False, print_raw=False)
hr_monitor.sensor = spo2_sensor

def log_sensor_data():
    """Main function with corrected CSV logging"""
    try:
        hr_monitor.start_sensor()
        
        # Wait for sensor stabilization
        print("\n🔄 Waiting for sensors to stabilize...")
        print("📍 Please place your finger GENTLY on the MAX30102 sensor")
        print("   - Cover both LED and photodiode")
        print("   - Light pressure, keep still")
        time.sleep(3)
        
        # Create CSV file with timestamp
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fall_detection_data_{timestamp_str}.csv"
        
        print(f"\n📊 Starting data logging to: {filename}")
        print("Press Ctrl+C to stop logging\n")
        
        # CSV file handling with proper structure
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            # Define exact fieldnames for 6-axis + vitals
            fieldnames = [
                'timestamp', 'datetime',
                'ax', 'ay', 'az',           # Accelerometer (g)
                'gx', 'gy', 'gz',           # Gyroscope (°/s)  
                'temp',                     # Temperature (°C)
                'bpm', 'spo2',             # Vital signs
                'finger_detected'           # Status flag
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            print("CSV Header written. Starting data collection...")
            
            sample_count = 0
            last_console_time = 0
            
            while True:
                current_time = time.time()
                datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                
                # Read IMU data
                imu_data = imu.read_data()
                
                if imu_data is None:
                    print("⚠️  IMU data not available, skipping...")
                    time.sleep(0.1)
                    continue
                
                # Get vital signs
                bpm = getattr(hr_monitor, 'bpm', 0) or 0
                spo2 = getattr(hr_monitor, 'spo2', None)
                finger_detected = bpm > 0
                
                # Prepare data row with all values explicitly
                data_row = {
                    'timestamp': round(current_time, 3),
                    'datetime': datetime_str,
                    'ax': imu_data['ax'],
                    'ay': imu_data['ay'], 
                    'az': imu_data['az'],
                    'gx': imu_data['gx'],
                    'gy': imu_data['gy'],
                    'gz': imu_data['gz'],
                    'spo2': spo2 if spo2 is not None else '',  # Empty string instead of None
                    'finger_detected': finger_detected
                }
                
                # Write to CSV
                writer.writerow(data_row)
                csvfile.flush()  # Force write to disk immediately
                
                sample_count += 1
                
                # Console output every 2 seconds
                if current_time - last_console_time >= 2.0:
                    finger_status = "👆 ON " if finger_detected else "👋 OFF"
                    spo2_display = f"{spo2:.1f}%" if spo2 is not None else "---"
                    
                    print(f"[{sample_count:04d}] {datetime_str[:19]} | "
                          f"Finger: {finger_status} | "
                          f"Accel: ({imu_data['ax']:+.3f}, {imu_data['ay']:+.3f}, {imu_data['az']:+.3f}) | "
                          f"Gyro: ({imu_data['gx']:+.1f}, {imu_data['gy']:+.1f}, {imu_data['gz']:+.1f}) | "
                          f"SpO2: {spo2_display}")
                    
                    last_console_time = current_time
                
                # 10Hz sampling rate (0.1 second intervals)
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print(f"\n\n🛑 Data collection stopped by user")
        hr_monitor.sensor.shutdown()
        
        # Final CSV verification
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
                print(f"✅ CSV file saved successfully: {filename}")
                print(f"📊 Total samples: {len(lines)-1}")  # -1 for header
                print(f"📁 File size: {len(open(filename).read())} bytes")
                
                if len(lines) > 1:
                    print("✅ Sample data row:")
                    print(f"   Header: {lines[0].strip()}")
                    print(f"   Data:   {lines[1].strip()}")
                    
        except Exception as e:
            print(f"❌ Error verifying CSV file: {e}")

if __name__ == "__main__":
    log_sensor_data()
