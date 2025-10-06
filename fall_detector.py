# fall_detector.py - Updated version with warning fixes
import joblib
import numpy as np
import pandas as pd
from collections import deque
import time
import warnings

# Suppress sklearn warnings
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')

class RealTimeFallDetector:
    def __init__(self, model_path):
        """Load the trained Random Forest model"""
        try:
            self.model = joblib.load(model_path)
            self.data_buffer = deque(maxlen=10)
            self.last_prediction_time = 0
            self.fall_detected = False
            self.fall_count = 0
            
            print("✅ Fall detection model loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading fall detection model: {e}")
            self.model = None
            
    def extract_features(self, sensor_data):
        """Extract features matching training data"""
        accel_magnitude = np.sqrt(sensor_data['ax']**2 + sensor_data['ay']**2 + sensor_data['az']**2)
        gyro_magnitude = np.sqrt(sensor_data['gx']**2 + sensor_data['gy']**2 + sensor_data['gz']**2)
        vertical_deviation = abs(sensor_data['az'] - 1.0)
        
        if len(self.data_buffer) > 0:
            prev_data = self.data_buffer[-1]
            prev_accel_mag = np.sqrt(prev_data['ax']**2 + prev_data['ay']**2 + prev_data['az']**2)
            prev_gyro_mag = np.sqrt(prev_data['gx']**2 + prev_data['gy']**2 + prev_data['gz']**2)
            accel_change = accel_magnitude - prev_accel_mag
            gyro_change = gyro_magnitude - prev_gyro_mag
        else:
            accel_change = 0
            gyro_change = 0
        
        return {
            'accel_magnitude': accel_magnitude,
            'gyro_magnitude': gyro_magnitude,
            'accel_change': accel_change,
            'gyro_change': gyro_change,
            'vertical_deviation': vertical_deviation
        }
    
    def predict_fall(self, sensor_data):
        """Predict fall with proper feature array"""
        if self.model is None:
            return {'fall_detected': False, 'confidence': 0.0, 'features': {}}
            
        features = self.extract_features(sensor_data)
        self.data_buffer.append(sensor_data)
        
        # Create feature DataFrame with proper column names (like training)
        feature_df = pd.DataFrame([features])
        
        try:
            prediction = self.model.predict(feature_df)[0]
            probability = self.model.predict_proba(feature_df)[0]
            confidence = max(probability)
            
            return {
                'fall_detected': bool(prediction),
                'confidence': confidence,
                'features': features,
                'timestamp': time.time()
            }
        except Exception as e:
            # Fallback to array method if DataFrame fails
            feature_array = np.array([[
                features['accel_magnitude'],
                features['gyro_magnitude'], 
                features['accel_change'],
                features['gyro_change'],
                features['vertical_deviation']
            ]])
            
            prediction = self.model.predict(feature_array)[0]
            probability = self.model.predict_proba(feature_array)[0]
            confidence = max(probability)
            
            return {
                'fall_detected': bool(prediction),
                'confidence': confidence,
                'features': features,
                'timestamp': time.time()
            }
    
    def process_sensor_reading(self, sensor_data):
        """Process sensor reading with reduced false alarms"""
        result = self.predict_fall(sensor_data)
        
        # Only alert on high confidence falls
        if result['fall_detected'] and result['confidence'] > 0.8:
            if not self.fall_detected:
                self.fall_detected = True
                self.fall_count += 1
                self.send_fall_alert(result)
                self.last_prediction_time = time.time()
        
        # Reset fall status after 3 seconds
        if self.fall_detected and (time.time() - self.last_prediction_time) > 3:
            self.fall_detected = False
            
        return result
    
    def send_fall_alert(self, result):
        """Send fall alert"""
        print("\n" + "🚨" * 15)
        print(f"   FALL DETECTED #{self.fall_count}!")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Accel: {result['features']['accel_magnitude']:.3f}g")
        print(f"   Gyro: {result['features']['gyro_magnitude']:.1f}°/s")
        print(f"   Time: {time.strftime('%H:%M:%S')}")
        print("🚨" * 15 + "\n")
