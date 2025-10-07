# app.py - Flask backend for health dashboard
from flask import Flask, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import json
import time
import threading
import pandas as pd
import glob
import os
from datetime import datetime

# Environment variables
from dotenv import load_dotenv
load_dotenv()

# Try to import health analyzer (with error handling)
try:
    from health_analyzer import HealthAnalyzer
    HEALTH_AI_AVAILABLE = True
    print("✅ Health analyzer import successful")
except ImportError as e:
    print(f"⚠️ Health analyzer not available: {e}")
    HEALTH_AI_AVAILABLE = False
except Exception as e:
    print(f"❌ Health analyzer import error: {e}")
    HEALTH_AI_AVAILABLE = False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'health-monitor-secret'

# Enable CORS for all routes
CORS(app, origins=["http://localhost:3000"])

socketio = SocketIO(app, cors_allowed_origins=["http://localhost:3000"])

# Global variable to store latest sensor data
latest_data = {
    'heart_rate': None,
    'spo2': None,
    'accel_magnitude': 0,
    'gyro_magnitude': 0,
    'fall_detected': False,
    'fall_confidence': 0,
    'timestamp': time.time(),
    'datetime': datetime.now().strftime('%H:%M:%S'),
    'device_status': 'offline'
}

# Initialize AI analyzer
health_ai = None
if HEALTH_AI_AVAILABLE:
    try:
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if gemini_api_key:
            health_ai = HealthAnalyzer(gemini_api_key)
            print("🤖 AI Health Analyzer loaded successfully")
        else:
            print("⚠️ Gemini API key not found in .env file")
    except Exception as e:
        print(f"⚠️ AI Analyzer initialization failed: {e}")
        health_ai = None

# ===== BASIC ROUTES =====
@app.route('/')
def index():
    return jsonify({
        "status": "🏥 Health Monitor API Running",
        "version": "2.0",
        "endpoints": {
            "current": "/api/current",
            "history": "/api/history/<minutes>",
            "generate_report": "/api/generate-report",
            "quick_analysis": "/api/quick-analysis"
        },
        "ai_status": "Available" if health_ai else "Not Available"
    })

@app.route('/api/status')
def api_status():
    return jsonify({
        "api_running": True,
        "ai_available": health_ai is not None,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/current')
def get_current_data():
    """Get current sensor readings"""
    return jsonify(latest_data)

@app.route('/api/history/<int:minutes>')
def get_history(minutes):
    """Get historical data for charts"""
    try:
        # Look for CSV files in parent directory (where main.py runs) - go up two levels
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_pattern = os.path.join(base_path, 'fall_detection_data_*.csv')
        csv_files = glob.glob(csv_pattern)
        
        print(f"🔍 Looking for CSV files at: {csv_pattern}")
        print(f"📁 Found {len(csv_files)} CSV files")
        
        if not csv_files:
            return jsonify([])
        
        # Get the most recent CSV file
        latest_csv = max(csv_files, key=os.path.getctime)
        df = pd.read_csv(latest_csv)
        
        # Get last N minutes of data
        if len(df) > 0:
            cutoff_time = time.time() - (minutes * 60)
            recent_data = df[df['timestamp'] > cutoff_time]
            
            # Format for frontend charts
            history = []
            for _, row in recent_data.iterrows():
                history.append({
                    'timestamp': int(row['timestamp'] * 1000),  # JavaScript timestamp
                    'heart_rate': float(row['bpm']) if row['bpm'] > 0 else None,
                    'spo2': row.get('spo2', None) if pd.notna(row.get('spo2', None)) and row.get('spo2', '') != '' else None,
                    'accel_magnitude': float(row['accel_magnitude']),
                    'gyro_magnitude': float(row['gyro_magnitude']),
                    'fall_detected': bool(row['fall_predicted']),
                    'fall_confidence': float(row['fall_confidence'])
                })
            
            return jsonify(history)
        
        return jsonify([])
        
    except Exception as e:
        print(f"❌ Error getting history: {e}")
        return jsonify({'error': str(e)}), 500

# ===== AI ROUTES =====
@app.route('/api/generate-report', methods=['GET', 'POST'])
def generate_health_report():
    """Generate AI-powered health report from latest CSV"""
    print("📊 Generate report endpoint called")
    
    try:
        if not health_ai:
            print("⚠️ Health AI not available")
            return jsonify({
                'error': 'AI analyzer not available',
                'details': 'Gemini API key not configured or health_analyzer.py not found'
            }), 500
        
        # Find the most recent CSV file - go up two levels from backend folder
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_pattern = os.path.join(base_path, 'fall_detection_data_*.csv')
        csv_files = glob.glob(csv_pattern)
        
        print(f"🔍 Looking for CSV files at: {csv_pattern}")
        print(f"📁 Found {len(csv_files)} CSV files")
        
        if not csv_files:
            print("❌ No CSV files found")
            return jsonify({
                'error': 'No data files found',
                'searched_path': csv_pattern
            }), 404
        
        latest_csv = max(csv_files, key=os.path.getctime)
        print(f"📄 Using CSV file: {latest_csv}")
        
        # Generate comprehensive report
        report = health_ai.generate_comprehensive_report(latest_csv)
        
        if report:
            print("✅ Report generated successfully")
            return jsonify(report)
        else:
            print("❌ Failed to generate report")
            return jsonify({'error': 'Failed to generate report'}), 500
            
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'type': 'server_error'}), 500

@app.route('/api/quick-analysis', methods=['GET', 'POST'])
def quick_analysis():
    """Get quick health analysis without full AI report"""
    print("📈 Quick analysis endpoint called")
    
    try:
        if not health_ai:
            return jsonify({'error': 'AI analyzer not available'}), 500
        
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_pattern = os.path.join(base_path, 'fall_detection_data_*.csv')
        csv_files = glob.glob(csv_pattern)
        
        if not csv_files:
            return jsonify({'error': 'No data files found'}), 404
        
        latest_csv = max(csv_files, key=os.path.getctime)
        analysis = health_ai.analyze_csv_data(latest_csv)
        
        return jsonify(analysis)
            
    except Exception as e:
        print(f"❌ Error in quick analysis: {e}")
        return jsonify({'error': str(e)}), 500

# ===== BACKGROUND DATA PROCESSING =====
def update_sensor_data():
    """Background thread to read sensor data and emit real-time updates"""
    print("📡 Starting sensor data monitoring...")
    
    while True:
        try:
            # Look for the most recent CSV file - go up two levels from backend
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            csv_pattern = os.path.join(base_path, 'fall_detection_data_*.csv')
            csv_files = glob.glob(csv_pattern)
            
            if csv_files:
                latest_csv = max(csv_files, key=os.path.getctime)
                df = pd.read_csv(latest_csv)
                
                if len(df) > 0:
                    # Get the last row (most recent data)
                    latest_row = df.iloc[-1]
                    
                    # Update global data
                    global latest_data
                    latest_data = {
                        'heart_rate': float(latest_row['bpm']) if latest_row['bpm'] > 0 else None,
                        'spo2': latest_row.get('spo2', None) if pd.notna(latest_row.get('spo2', None)) and latest_row.get('spo2', '') != '' else None,
                        'accel_magnitude': float(latest_row['accel_magnitude']),
                        'gyro_magnitude': float(latest_row['gyro_magnitude']),
                        'fall_detected': bool(latest_row['fall_predicted']),
                        'fall_confidence': float(latest_row['fall_confidence']),
                        'temperature': float(latest_row['temp']),
                        'timestamp': time.time(),
                        'datetime': datetime.now().strftime('%H:%M:%S'),
                        'device_status': 'online'
                    }
                    
                    # Emit to all connected WebSocket clients
                    socketio.emit('sensor_update', latest_data)
            else:
                # No CSV files found - sensor might be offline
                latest_data['device_status'] = 'offline'
                latest_data['datetime'] = datetime.now().strftime('%H:%M:%S')
            
            time.sleep(1)  # Update every second
            
        except Exception as e:
            print(f"❌ Error in sensor monitoring: {e}")
            time.sleep(5)  # Wait longer on error

# ===== WEBSOCKET HANDLERS =====
@socketio.on('connect')
def handle_connect():
    print(f"👤 Client connected from dashboard")
    emit('sensor_update', latest_data)

@socketio.on('disconnect')
def handle_disconnect():
    print("👤 Client disconnected")

@socketio.on('request_history')
def handle_history_request(data):
    """Handle real-time history requests"""
    minutes = data.get('minutes', 10)
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_pattern = os.path.join(base_path, 'fall_detection_data_*.csv')
        csv_files = glob.glob(csv_pattern)
        
        if csv_files:
            latest_csv = max(csv_files, key=os.path.getctime)
            df = pd.read_csv(latest_csv)
            
            cutoff_time = time.time() - (minutes * 60)
            recent_data = df[df['timestamp'] > cutoff_time]
            
            history = []
            for _, row in recent_data.iterrows():
                history.append({
                    'timestamp': int(row['timestamp'] * 1000),
                    'heart_rate': float(row['bpm']) if row['bpm'] > 0 else None,
                    'spo2': row.get('spo2', None) if pd.notna(row.get('spo2', None)) and row.get('spo2', '') != '' else None,
                    'accel_magnitude': float(row['accel_magnitude']),
                })
            
            emit('history_data', history)
    except Exception as e:
        print(f"Error sending history: {e}")

if __name__ == '__main__':
    print("🚀 Health Monitor Dashboard Backend Starting...")
    print("🏥 Monitoring sensor data from CSV files")
    print("📡 WebSocket server running on http://localhost:5000")
    print("🌐 CORS enabled for frontend connections")
    print(f"🤖 AI Health Analyzer: {'Available' if health_ai else 'Not Available'}")
    
    # Start background sensor monitoring thread
    sensor_thread = threading.Thread(target=update_sensor_data)
    sensor_thread.daemon = True
    sensor_thread.start()
    
    # List available routes for debugging
    print("\n📋 Available API endpoints:")
    for rule in app.url_map.iter_rules():
        print(f"   {rule.rule} -> {rule.endpoint}")
    
    # Run Flask-SocketIO server
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
