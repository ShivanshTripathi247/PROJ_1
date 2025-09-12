import time
import csv
import struct
import smbus2 as smbus
from datetime import datetime
from max30102.enhanced_heartrate_monitor import EnhancedHeartRateMonitor
from ppg2abp_integration import SimpleBPEstimator

# Your existing IMU class (unchanged)
bus = smbus.SMBus(1)
MPU9250_ADDR = 0x68
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B

class IMU6Axis:
    def __init__(self):
        self.setup_mpu()
    
    def setup_mpu(self):
        try:
            bus.write_byte_data(MPU9250_ADDR, PWR_MGMT_1, 0x00)
            time.sleep(0.1)
            print("✅ 6-axis IMU initialized successfully")
            self.available = True
        except Exception as e:
            print(f"❌ IMU initialization failed: {e}")
            self.available = False
    
    def read_data(self):
        if not self.available:
            return None
        try:
            raw_data = bus.read_i2c_block_data(MPU9250_ADDR, ACCEL_XOUT_H, 14)
            ax = struct.unpack('>h', bytes(raw_data[0:2]))[0] / 16384.0
            ay = struct.unpack('>h', bytes(raw_data[2:4]))[0] / 16384.0
            az = struct.unpack('>h', bytes(raw_data[4:6]))[0] / 16384.0
            temp = struct.unpack('>h', bytes(raw_data[6:8]))[0] / 340.0 + 36.53
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

def enhanced_log_sensor_data():
    """Enhanced logging with blood pressure estimation"""
    
    # Initialize sensors
    print("Initializing enhanced sensors...")
    imu = IMU6Axis()
    hr_monitor = EnhancedHeartRateMonitor(print_result=False)  # Using enhanced version
    bp_estimator = SimpleBPEstimator()
    
    try:
        hr_monitor.start_sensor()
        
        print("\n🔄 Waiting for sensors to stabilize...")
        print("📍 Please place your finger GENTLY on the MAX30102 sensor")
        time.sleep(3)
        
        # Create enhanced CSV with BP columns
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"enhanced_health_data_{timestamp_str}.csv"
        
        print(f"\n📊 Starting enhanced data logging to: {filename}")
        print("🩸 Blood pressure estimation will begin after 20 seconds...")
        print("Press Ctrl+C to stop logging\n")
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'timestamp', 'datetime',
                'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'temp',
                'bpm', 'spo2', 'finger_detected',
                'bp_systolic', 'bp_diastolic', 'bp_estimated'  # New BP fields
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            sample_count = 0
            last_console_time = 0
            last_bp_check = 0
            
            while True:
                current_time = time.time()
                datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                
                # Read IMU data
                imu_data = imu.read_data()
                if imu_data is None:
                    time.sleep(0.1)
                    continue
                
                # Get vital signs
                bpm = getattr(hr_monitor, 'bpm', 0) or 0
                spo2 = getattr(hr_monitor, 'spo2', None)
                finger_detected = bpm > 0
                
                # Get raw PPG for blood pressure (if available)
                ir_data, red_data, timestamps = hr_monitor.get_raw_ppg_data(duration_seconds=20)
                if ir_data and len(ir_data) > 0:
                    # Add latest PPG sample to BP estimator
                    bp_estimator.add_ppg_sample(ir_data[-1], current_time)
                
                # Estimate blood pressure every 30 seconds
                bp_systolic, bp_diastolic, bp_estimated = None, None, False
                if current_time - last_bp_check >= 30:  # Every 30 seconds
                    bp_sys, bp_dia = bp_estimator.estimate_blood_pressure()
                    if bp_sys and bp_dia:
                        bp_systolic, bp_diastolic, bp_estimated = bp_sys, bp_dia, True
                        print(f"🩸 BP Estimated: {bp_sys:.1f}/{bp_dia:.1f} mmHg")
                    last_bp_check = current_time
                
                # Prepare enhanced data row
                data_row = {
                    'timestamp': round(current_time, 3),
                    'datetime': datetime_str,
                    'ax': imu_data['ax'], 'ay': imu_data['ay'], 'az': imu_data['az'],
                    'gx': imu_data['gx'], 'gy': imu_data['gy'], 'gz': imu_data['gz'],
                    'temp': imu_data['temp'],
                    'bpm': bpm,  # ← FIXED: Now included!
                    'spo2': spo2 if spo2 is not None else '',
                    'finger_detected': finger_detected,
                    'bp_systolic': bp_systolic if bp_systolic else '',
                    'bp_diastolic': bp_diastolic if bp_diastolic else '',
                    'bp_estimated': bp_estimated
                }
                
                # Write to CSV
                writer.writerow(data_row)
                csvfile.flush()
                sample_count += 1
                
                # Enhanced console output every 2 seconds
                if current_time - last_console_time >= 2.0:
                    finger_status = "👆 ON " if finger_detected else "👋 OFF"
                    spo2_display = f"{spo2:.1f}%" if spo2 is not None else "---"
                    bp_display = f"{bp_systolic:.1f}/{bp_diastolic:.1f}" if bp_systolic else "Estimating..."
                    
                    print(f"[{sample_count:04d}] {datetime_str[:19]} | "
                          f"Finger: {finger_status} | "
                          f"HR: {bpm:.0f} BPM | SpO2: {spo2_display} | "
                          f"BP: {bp_display} mmHg | "
                          f"IMU: ({imu_data['ax']:+.2f}, {imu_data['ay']:+.2f}, {imu_data['az']:+.2f})")
                    
                    last_console_time = current_time
                
                time.sleep(0.02)  # 50Hz sampling
                
    except KeyboardInterrupt:
        print(f"\n\n🛑 Enhanced data collection stopped by user")
        hr_monitor.stop_sensor()
        
        print(f"✅ Enhanced CSV file saved: {filename}")
        print("📊 Data includes: IMU + HR + SpO2 + Blood Pressure estimates")

if __name__ == "__main__":
    enhanced_log_sensor_data()
