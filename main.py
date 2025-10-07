import time
import csv
import struct
import smbus2 as smbus
from datetime import datetime
from max30102.max30102 import MAX30102
from max30102.heartrate_monitor import HeartRateMonitor
from gps_module import GPSTracker, EmergencyAlertSystem
import fcntl
import threading
import warnings

# Suppress sklearn warnings
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')

# Try to import fall detector (with error handling)
try:
    from fall_detector import RealTimeFallDetector
    FALL_DETECTION_ENABLED = True
except ImportError as e:
    print(f"⚠️  Fall detection not available: {e}")
    FALL_DETECTION_ENABLED = False

# I2C bus and addresses
bus = smbus.SMBus(1)
MPU9250_ADDR = 0x68

# MPU9250 registers (6-axis only)
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B

# I2C lock for thread safety
i2c_lock = threading.Lock()

class IMU6Axis:
    def __init__(self):
        self.setup_mpu()
        
    def setup_mpu(self):
        """Initialize MPU9250 for 6-axis readings only"""
        try:
            with i2c_lock:
                bus.write_byte_data(MPU9250_ADDR, PWR_MGMT_1, 0x00)
                time.sleep(0.1)
            print("✅ 6-axis IMU initialized successfully")
            self.available = True
        except Exception as e:
            print(f"❌ IMU initialization failed: {e}")
            self.available = False
    
    def read_data(self):
        """Read accelerometer and gyroscope data with I2C protection"""
        if not self.available:
            return None
            
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with i2c_lock:
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
                if attempt < max_retries - 1:
                    time.sleep(0.01 * (attempt + 1))  # Progressive delay
                    continue
                else:
                    # Only print error on final attempt to reduce spam
                    if attempt == max_retries - 1:
                        print(f"❌ IMU read error after {max_retries} attempts: {e}")
                    return None
        
        return None

# Initialize sensors
print("Initializing sensors...")
imu = IMU6Axis()

# Initialize heart rate sensor with different I2C instance if needed
try:
    spo2_sensor = MAX30102()
    hr_monitor = HeartRateMonitor(print_result=False, print_raw=False)
    hr_monitor.sensor = spo2_sensor
    print("✅ Heart rate sensor initialized")
except Exception as e:
    print(f"⚠️  Heart rate sensor initialization failed: {e}")
    spo2_sensor = None
    hr_monitor = None

# Initialize GPS tracking
print("📡 Initializing GPS...")
try:
    gps_tracker = GPSTracker()
    emergency_system = EmergencyAlertSystem(gps_tracker)
    print("✅ GPS modules initialized")
except Exception as e:
    print(f"⚠️  GPS initialization failed: {e}")
    gps_tracker = None
    emergency_system = None

# Initialize fall detector
if FALL_DETECTION_ENABLED:
    try:
        fall_detector = RealTimeFallDetector('fall_detector_model.pkl')
    except Exception as e:
        print(f"⚠️  Fall detector initialization failed: {e}")
        FALL_DETECTION_ENABLED = False

def log_sensor_data():
    """Main function with improved I2C handling and fall detection"""
    try:
        # Start heart rate monitoring if available
        if hr_monitor:
            hr_monitor.start_sensor()
        
        # Start GPS tracking if available
        gps_started = False
        if gps_tracker:
            gps_started = gps_tracker.start()
            if gps_started:
                print("✅ GPS tracking started")
            else:
                print("⚠️ GPS failed to start, continuing without GPS")
        
        # Wait for sensor stabilization
        print("\n🔄 Waiting for sensors to stabilize...")
        if hr_monitor:
            print("📍 Please place your finger GENTLY on the MAX30102 sensor")
            print("   - Cover both LED and photodiode")
            print("   - Light pressure, keep still")
        if FALL_DETECTION_ENABLED:
            print("🤖 Fall detection is ACTIVE")
            print("🧪 Try dropping/shaking the device to test fall detection!")
        if gps_started:
            print("🛰️  GPS tracking is ACTIVE - location data will be included")
        time.sleep(3)
        
        # Create CSV file with timestamp
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fall_detection_data_{timestamp_str}.csv"
        
        print(f"\n📊 Starting data logging to: {filename}")
        print("Press Ctrl+C to stop logging\n")
        
        # CSV file handling with fall detection columns
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            # Define fieldnames including fall detection
            fieldnames = [
                'timestamp', 'datetime',
                'ax', 'ay', 'az',           # Accelerometer (g)
                'gx', 'gy', 'gz',           # Gyroscope (°/s)  
                'temp',                     # Temperature (°C)
                'bpm', 'spo2',             # Vital signs
                'finger_detected',          # Status flag
                'fall_predicted',           # Fall prediction (0/1)
                'fall_confidence',          # Confidence score
                'accel_magnitude',          # Feature for analysis
                'gyro_magnitude'            # Feature for analysis
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            print("CSV Header written. Starting data collection...")
            
            sample_count = 0
            last_console_time = 0
            successful_reads = 0
            failed_reads = 0
            
            while True:
                current_time = time.time()
                datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                
                # Read IMU data with better error handling
                imu_data = imu.read_data()
                
                if imu_data is None:
                    failed_reads += 1
                    if failed_reads % 10 == 0:  # Only print every 10th failure
                        print(f"⚠️  IMU data unavailable (failed: {failed_reads}, success: {successful_reads})")
                    time.sleep(0.05)  # Shorter delay for faster recovery
                    continue
                
                successful_reads += 1
                
                # Get vital signs with error handling
                bpm = 0
                spo2 = None
                finger_detected = False
                
                if hr_monitor:
                    try:
                        bpm = getattr(hr_monitor, 'bpm', 0) or 0
                        spo2 = getattr(hr_monitor, 'spo2', None)
                        finger_detected = bpm > 0
                    except Exception as e:
                        pass  # Ignore heart rate errors
                
                # Fall detection processing
                fall_predicted = False
                fall_confidence = 0.0
                accel_magnitude = 0.0
                gyro_magnitude = 0.0
                
                if FALL_DETECTION_ENABLED:
                    try:
                        # Prepare sensor data for fall detection
                        sensor_data = {
                            'ax': imu_data['ax'],
                            'ay': imu_data['ay'], 
                            'az': imu_data['az'],
                            'gx': imu_data['gx'],
                            'gy': imu_data['gy'],
                            'gz': imu_data['gz']
                        }
                        
                        # Process fall detection
                        fall_result = fall_detector.process_sensor_reading(sensor_data)
                        fall_predicted = fall_result['fall_detected']
                        fall_confidence = fall_result['confidence']
                        
                        # Handle fall detection alert
                        if fall_predicted:
                            print("🚨 FALL DETECTED! Sending emergency alert...")
                            
                            # Prepare fall data for alert
                            fall_alert_data = {
                                'confidence': fall_confidence,
                                'heart_rate': bpm,
                                'accel_magnitude': accel_magnitude,
                                'temperature': imu_data['temp'],
                                'timestamp': datetime_str
                            }
                            
                            # Send emergency alert with GPS location
                            if gps_started and emergency_system:
                                try:
                                    alert_message = emergency_system.send_fall_alert(fall_alert_data)
                                    print(f"📞 Emergency alert sent: {alert_message}")
                                except Exception as e:
                                    print(f"❌ Failed to send emergency alert: {e}")
                            else:
                                print("⚠️ Fall detected but GPS/Emergency system not available")
                        
                        if 'features' in fall_result:
                            accel_magnitude = fall_result['features'].get('accel_magnitude', 0.0)
                            gyro_magnitude = fall_result['features'].get('gyro_magnitude', 0.0)
                    except Exception as e:
                        # Calculate basic magnitudes if fall detection fails
                        accel_magnitude = (imu_data['ax']**2 + imu_data['ay']**2 + imu_data['az']**2)**0.5
                        gyro_magnitude = (imu_data['gx']**2 + imu_data['gy']**2 + imu_data['gz']**2)**0.5
                
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
                    'temp': imu_data['temp'],
                    'bpm': bpm,
                    'spo2': spo2 if spo2 is not None else '',
                    'finger_detected': finger_detected,
                    'fall_predicted': fall_predicted,
                    'fall_confidence': round(fall_confidence, 3),
                    'accel_magnitude': round(accel_magnitude, 3),
                    'gyro_magnitude': round(gyro_magnitude, 3)
                }
                
                # Write to CSV
                writer.writerow(data_row)
                csvfile.flush()  # Force write to disk immediately
                
                sample_count += 1
                
                # Console output every 2 seconds
                if current_time - last_console_time >= 2.0:
                    finger_status = "👆 ON " if finger_detected else "👋 OFF"
                    spo2_display = f"{spo2:.1f}%" if spo2 is not None else "---"
                    bpm_display = f"{bpm} BPM" if bpm > 0 else "--- BPM"
                    
                    fall_status = ""
                    if FALL_DETECTION_ENABLED:
                        if fall_predicted:
                            fall_status = f"🚨 FALL RISK: {fall_confidence:.2f}"
                        else:
                            fall_status = f"✅ Safe ({fall_confidence:.2f})"
                    
                    # Calculate current acceleration for display
                    current_accel_mag = (imu_data['ax']**2 + imu_data['ay']**2 + imu_data['az']**2)**0.5
                    
                    print(f"[{sample_count:04d}] {datetime_str[:19]} | "
                          f"Finger: {finger_status} | "
                          f"HR: {bpm_display} | "
                          f"SpO2: {spo2_display}")
                    print(f"         Accel: ({imu_data['ax']:+.3f}, {imu_data['ay']:+.3f}, {imu_data['az']:+.3f}) "
                          f"Mag: {current_accel_mag:.3f}g | "
                          f"Gyro: ({imu_data['gx']:+.1f}, {imu_data['gy']:+.1f}, {imu_data['gz']:+.1f})")
                    
                    if FALL_DETECTION_ENABLED:
                        print(f"         Fall Detection: {fall_status}")
                    
                    print(f"         I2C Status: ✅{successful_reads} ❌{failed_reads}")
                    print()
                    
                    last_console_time = current_time
                
                # 10Hz sampling rate (0.1 second intervals)
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print(f"\n\n🛑 Data collection stopped by user")
        
        # Clean up sensors
        if hr_monitor:
            hr_monitor.sensor.shutdown()
        
        # Clean up GPS when stopping
        if gps_started and gps_tracker:
            print("📡 Stopping GPS tracking...")
            gps_tracker.stop()
        
        # Final CSV verification
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
                print(f"✅ CSV file saved successfully: {filename}")
                print(f"📊 Total samples: {len(lines)-1}")  # -1 for header
                print(f"📁 File size: {len(open(filename).read())} bytes")
                print(f"📈 I2C Success rate: {successful_reads/(successful_reads+failed_reads)*100:.1f}%")
                
                if FALL_DETECTION_ENABLED:
                    print(f"🤖 Fall detection was active during recording")
                if gps_started:
                    print(f"🛰️  GPS tracking was active during recording")
                    
        except Exception as e:
            print(f"❌ Error verifying CSV file: {e}")

if __name__ == "__main__":
    log_sensor_data()
