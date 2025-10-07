# gps_module.py - GPS functionality for emergency alerts
import serial
import pynmea2
import threading
import time
import json
from datetime import datetime
import requests

class GPSTracker:
    def __init__(self, serial_port='/dev/ttyS0', baud_rate=9600):
        """Initialize GPS tracker"""
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.ser = None
        self.running = False
        
        # GPS data
        self.current_location = {
            'latitude': None,
            'longitude': None,
            'altitude': None,
            'speed': None,
            'course': None,
            'timestamp': None,
            'fix_quality': 0,
            'satellites': 0,
            'gps_status': 'initializing'
        }
        
        # Thread for GPS reading
        self.gps_thread = None
        
    def start(self):
        """Start GPS tracking"""
        try:
            self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            self.running = True
            
            # Start GPS reading thread
            self.gps_thread = threading.Thread(target=self._read_gps_data)
            self.gps_thread.daemon = True
            self.gps_thread.start()
            
            print("📡 GPS Tracker started successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start GPS: {e}")
            return False
    
    def stop(self):
        """Stop GPS tracking"""
        self.running = False
        if self.ser:
            self.ser.close()
        print("📡 GPS Tracker stopped")
    
    def _read_gps_data(self):
        """Background thread to read GPS data"""
        print("📡 Starting GPS data reading...")
        
        while self.running:
            try:
                if self.ser and self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    if line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                        # Global Positioning System Fix Data
                        self._parse_gga(line)
                    elif line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                        # Recommended Minimum Course
                        self._parse_rmc(line)
                        
                time.sleep(0.1)  # Small delay to prevent CPU overload
                
            except Exception as e:
                print(f"❌ GPS reading error: {e}")
                time.sleep(1)
    
    def _parse_gga(self, sentence):
        """Parse GPGGA sentence"""
        try:
            msg = pynmea2.parse(sentence)
            
            self.current_location.update({
                'latitude': float(msg.latitude) if msg.latitude else None,
                'longitude': float(msg.longitude) if msg.longitude else None,
                'altitude': float(msg.altitude) if msg.altitude else None,
                'fix_quality': int(msg.gps_qual) if msg.gps_qual else 0,
                'satellites': int(msg.num_sats) if msg.num_sats else 0,
                'timestamp': datetime.now().isoformat()
            })
            
            # Update GPS status
            if self.current_location['fix_quality'] > 0:
                self.current_location['gps_status'] = 'fixed'
            else:
                self.current_location['gps_status'] = 'searching'
                
        except Exception as e:
            print(f"❌ Error parsing GGA: {e}")
    
    def _parse_rmc(self, sentence):
        """Parse GPRMC sentence"""
        try:
            msg = pynmea2.parse(sentence)
            
            if msg.speed:
                self.current_location['speed'] = float(msg.speed) * 1.852  # Convert knots to km/h
            if msg.true_course:
                self.current_location['course'] = float(msg.true_course)
                
        except Exception as e:
            print(f"❌ Error parsing RMC: {e}")
    
    def get_location(self):
        """Get current GPS location"""
        return self.current_location.copy()
    
    def is_location_valid(self):
        """Check if GPS has valid location"""
        return (self.current_location['latitude'] is not None and 
                self.current_location['longitude'] is not None and
                self.current_location['fix_quality'] > 0)
    
    def get_google_maps_link(self):
        """Generate Google Maps link for current location"""
        if self.is_location_valid():
            lat = self.current_location['latitude']
            lon = self.current_location['longitude']
            return f"https://maps.google.com/maps?q={lat},{lon}"
        return None
    
    def get_location_string(self):
        """Get human-readable location string"""
        if self.is_location_valid():
            lat = self.current_location['latitude']
            lon = self.current_location['longitude']
            return f"Lat: {lat:.6f}, Lon: {lon:.6f}"
        return "Location not available"

# Emergency Alert System
class EmergencyAlertSystem:
    def __init__(self, gps_tracker):
        """Initialize emergency alert system"""
        self.gps_tracker = gps_tracker
        self.emergency_contacts = [
            "+1234567890",  # Add real emergency contact numbers
            "+0987654321"
        ]
        
    def send_fall_alert(self, fall_data):
        """Send emergency alert when fall is detected"""
        location = self.gps_tracker.get_location()
        maps_link = self.gps_tracker.get_google_maps_link()
        
        alert_message = self._create_alert_message(fall_data, location, maps_link)
        
        # Send alerts through multiple channels
        self._send_console_alert(alert_message)
        # self._send_sms_alert(alert_message)  # Uncomment when SMS service is configured
        self._save_emergency_log(fall_data, location)
        
        return alert_message
    
    def _create_alert_message(self, fall_data, location, maps_link):
        """Create emergency alert message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""
🚨 EMERGENCY FALL ALERT 🚨

Time: {timestamp}
Confidence: {fall_data.get('confidence', 0)*100:.1f}%

📍 Location: {self.gps_tracker.get_location_string()}
GPS Status: {location.get('gps_status', 'unknown')}
"""
        
        if maps_link:
            message += f"\n🗺️ Maps: {maps_link}"
        else:
            message += f"\n⚠️ GPS location not available"
            
        message += f"""

📊 Sensor Data:
- Heart Rate: {fall_data.get('heart_rate', 'N/A')} BPM
- Acceleration: {fall_data.get('accel_magnitude', 0):.2f}g
- Temperature: {fall_data.get('temperature', 'N/A')}°C

🆘 Please check on the person immediately!
"""
        
        return message
    
    def _send_console_alert(self, message):
        """Send alert to console (for testing)"""
        print("\n" + "="*60)
        print("🚨 EMERGENCY ALERT TRIGGERED 🚨")
        print("="*60)
        print(message)
        print("="*60)
    
    def _send_sms_alert(self, message):
        """Send SMS alert (requires SMS service configuration)"""
        # Example using Twilio (requires account setup)
        # from twilio.rest import Client
        
        # Replace with your SMS service implementation
        print("📱 SMS Alert would be sent to:", self.emergency_contacts)
    
    def _save_emergency_log(self, fall_data, location):
        """Save emergency event to log file"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'fall_detected',
            'fall_data': fall_data,
            'gps_location': location,
            'maps_link': self.gps_tracker.get_google_maps_link()
        }
        
        try:
            with open('emergency_log.json', 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            print("📝 Emergency event logged")
        except Exception as e:
            print(f"❌ Failed to log emergency: {e}")

# Test GPS functionality
def test_gps():
    """Test GPS functionality"""
    gps = GPSTracker()
    
    if gps.start():
        print("📡 Testing GPS for 30 seconds...")
        
        for i in range(30):
            location = gps.get_location()
            print(f"[{i+1:2d}/30] GPS Status: {location['gps_status']} | "
                  f"Location: {gps.get_location_string()} | "
                  f"Satellites: {location['satellites']}")
            time.sleep(1)
        
        if gps.is_location_valid():
            print(f"\n✅ GPS Working! Maps Link: {gps.get_google_maps_link()}")
        else:
            print(f"\n⚠️ GPS needs more time to get fix. Try moving outside.")
            
        gps.stop()
    else:
        print("❌ Failed to start GPS")

if __name__ == "__main__":
    test_gps()
