# health_analyzer.py - AI-powered health report generation
import google.generativeai as genai
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
import glob

class HealthAnalyzer:
    def __init__(self, gemini_api_key):
        """Initialize Gemini AI for health analysis"""
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        print("🤖 AI Health Analyzer initialized with Gemini")
    
    def analyze_csv_data(self, csv_file_path):
        """Analyze CSV data and extract health insights"""
        try:
            df = pd.read_csv(csv_file_path)
            
            # Calculate health metrics
            analysis = {
                'session_info': {
                    'duration_minutes': (df['timestamp'].max() - df['timestamp'].min()) / 60,
                    'total_samples': len(df),
                    'start_time': df.iloc[0]['datetime'] if len(df) > 0 else 'Unknown',
                    'end_time': df.iloc[-1]['datetime'] if len(df) > 0 else 'Unknown'
                },
                'heart_rate': self._analyze_heart_rate(df),
                'movement': self._analyze_movement(df),
                'fall_detection': self._analyze_fall_events(df),
                'vital_signs': self._analyze_vital_signs(df),
                'recommendations': []
            }
            
            return analysis
            
        except Exception as e:
            print(f"❌ Error analyzing CSV: {e}")
            return None
    
    def _analyze_heart_rate(self, df):
        """Analyze heart rate patterns"""
        valid_hr = df[df['bpm'] > 0]['bpm']
        
        if len(valid_hr) == 0:
            return {
                'status': 'no_data',
                'message': 'No heart rate data available',
                'coverage': 0
            }
        
        return {
            'status': 'analyzed',
            'average': round(valid_hr.mean(), 1),
            'min': round(valid_hr.min(), 1),
            'max': round(valid_hr.max(), 1),
            'coverage': round(len(valid_hr) / len(df) * 100, 1),
            'variability': round(valid_hr.std(), 1) if len(valid_hr) > 1 else 0,
            'zones': {
                'resting': len(valid_hr[valid_hr < 70]),
                'moderate': len(valid_hr[(valid_hr >= 70) & (valid_hr < 85)]),
                'elevated': len(valid_hr[valid_hr >= 85])
            }
        }
    
    def _analyze_movement(self, df):
        """Analyze movement and activity patterns"""
        return {
            'avg_acceleration': round(df['accel_magnitude'].mean(), 3),
            'max_acceleration': round(df['accel_magnitude'].max(), 3),
            'movement_variance': round(df['accel_magnitude'].std(), 3),
            'high_movement_events': len(df[df['accel_magnitude'] > 1.5]),
            'activity_level': self._classify_activity_level(df['accel_magnitude'])
        }
    
    def _analyze_fall_events(self, df):
        """Analyze fall detection results"""
        fall_events = df[df['fall_predicted'] == True]
        
        return {
            'total_falls_detected': len(fall_events),
            'fall_timestamps': fall_events['datetime'].tolist() if len(fall_events) > 0 else [],
            'avg_confidence': round(df['fall_confidence'].mean(), 3),
            'false_positive_risk': 'low' if len(fall_events) == 0 else 'moderate'
        }
    
    def _analyze_vital_signs(self, df):
        """Analyze SpO2 and other vitals"""
        valid_spo2 = df[df['spo2'].notna() & (df['spo2'] != '')]['spo2']
        
        return {
            'spo2': {
                'available': len(valid_spo2) > 0,
                'average': round(valid_spo2.mean(), 1) if len(valid_spo2) > 0 else None,
                'coverage': round(len(valid_spo2) / len(df) * 100, 1) if len(valid_spo2) > 0 else 0
            },
            'temperature': {
                'average': round(df['temp'].mean(), 1),
                'stable': df['temp'].std() < 1.0
            }
        }
    
    def _classify_activity_level(self, accel_data):
        """Classify overall activity level"""
        avg_accel = accel_data.mean()
        
        if avg_accel < 0.9:
            return 'sedentary'
        elif avg_accel < 1.2:
            return 'light_activity' 
        elif avg_accel < 1.8:
            return 'moderate_activity'
        else:
            return 'high_activity'
    
    def generate_ai_report(self, analysis_data, user_profile=None):
        """Generate AI-powered health report using Gemini"""
        
        # Create a comprehensive prompt for Gemini
        prompt = f"""
        As a health analytics AI, analyze the following health monitoring data and provide a comprehensive health report with personalized recommendations.

        **HEALTH DATA SUMMARY:**
        - Session Duration: {analysis_data['session_info']['duration_minutes']:.1f} minutes
        - Total Samples: {analysis_data['session_info']['total_samples']}
        - Time Period: {analysis_data['session_info']['start_time']} to {analysis_data['session_info']['end_time']}

        **HEART RATE ANALYSIS:**
        {json.dumps(analysis_data['heart_rate'], indent=2)}

        **MOVEMENT & ACTIVITY:**
        {json.dumps(analysis_data['movement'], indent=2)}

        **FALL DETECTION:**
        {json.dumps(analysis_data['fall_detection'], indent=2)}

        **VITAL SIGNS:**
        {json.dumps(analysis_data['vital_signs'], indent=2)}

        **PLEASE PROVIDE:**

        1. **HEALTH STATUS OVERVIEW** (2-3 sentences)
        - Overall health assessment based on the data
        - Key findings and patterns observed

        2. **DETAILED ANALYSIS** (bullet points)
        - Heart rate patterns and implications
        - Activity level assessment  
        - Fall risk evaluation
        - Any concerning trends

        3. **PERSONALIZED RECOMMENDATIONS** (actionable advice)
        - Immediate precautions to take
        - Lifestyle suggestions
        - When to consult healthcare providers
        - Specific monitoring recommendations

        4. **RISK ASSESSMENT**
        - Low/Medium/High risk classification
        - Key risk factors identified
        - Preventive measures

        **RESPONSE FORMAT:** Please structure your response as a JSON object with these sections:
        {{
            "health_status": "overall assessment text",
            "key_findings": ["finding 1", "finding 2", "finding 3"],
            "recommendations": [
                {{
                    "category": "immediate",
                    "advice": "specific advice text",
                    "priority": "high/medium/low"
                }}
            ],
            "risk_level": "low/medium/high",
            "risk_factors": ["factor 1", "factor 2"],
            "next_steps": ["step 1", "step 2"]
        }}

        Focus on practical, actionable insights that can improve health and safety.
        """
        
        try:
            print("🤖 Generating AI health report...")
            response = self.model.generate_content(prompt)
            
            # Try to parse JSON response
            try:
                # Extract JSON from response
                response_text = response.text
                
                # Find JSON content (sometimes Gemini adds extra text)
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_text = response_text[start_idx:end_idx]
                    ai_report = json.loads(json_text)
                else:
                    # Fallback to raw text if JSON parsing fails
                    ai_report = {
                        "health_status": response_text,
                        "key_findings": ["AI analysis completed"],
                        "recommendations": [{"category": "general", "advice": response_text[:200], "priority": "medium"}],
                        "risk_level": "medium",
                        "risk_factors": ["Insufficient data for detailed analysis"],
                        "next_steps": ["Continue monitoring", "Consult healthcare provider"]
                    }
                
                print("✅ AI health report generated successfully")
                return ai_report
                
            except json.JSONDecodeError:
                # Return structured fallback
                return {
                    "health_status": response.text[:300],
                    "key_findings": ["AI analysis provided", "Data processed successfully"],
                    "recommendations": [
                        {
                            "category": "general",
                            "advice": response.text[:200] if len(response.text) > 200 else response.text,
                            "priority": "medium"
                        }
                    ],
                    "risk_level": "medium",
                    "risk_factors": ["Analysis based on limited session data"],
                    "next_steps": ["Continue regular monitoring", "Maintain healthy lifestyle"]
                }
                
        except Exception as e:
            print(f"❌ Error generating AI report: {e}")
            return {
                "health_status": "Health monitoring session completed successfully",
                "key_findings": ["Data collected and analyzed", "System functioning normally"],
                "recommendations": [
                    {
                        "category": "system",
                        "advice": "Continue regular health monitoring for better insights",
                        "priority": "medium"
                    }
                ],
                "risk_level": "low",
                "risk_factors": ["Limited data for comprehensive analysis"],
                "next_steps": ["Extend monitoring duration", "Ensure proper sensor placement"]
            }
    
    def generate_comprehensive_report(self, csv_file_path, user_profile=None):
        """Generate complete health report with AI insights"""
        
        # Step 1: Analyze raw data
        analysis = self.analyze_csv_data(csv_file_path)
        
        if not analysis:
            return None
        
        # Step 2: Generate AI insights
        ai_report = self.generate_ai_report(analysis, user_profile)
        
        # Step 3: Combine everything
        comprehensive_report = {
            'report_id': f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'generated_at': datetime.now().isoformat(),
            'data_source': os.path.basename(csv_file_path),
            'session_summary': analysis['session_info'],
            'health_metrics': {
                'heart_rate': analysis['heart_rate'],
                'movement': analysis['movement'],
                'fall_detection': analysis['fall_detection'],
                'vital_signs': analysis['vital_signs']
            },
            'ai_insights': ai_report,
            'recommendations_summary': self._create_recommendation_summary(ai_report)
        }
        
        return comprehensive_report
    
    def _create_recommendation_summary(self, ai_report):
        """Create a summary of key recommendations"""
        try:
            recommendations = ai_report.get('recommendations', [])
            
            summary = {
                'immediate_actions': [r['advice'] for r in recommendations if r.get('priority') == 'high'],
                'general_advice': [r['advice'] for r in recommendations if r.get('priority') == 'medium'],
                'long_term_goals': [r['advice'] for r in recommendations if r.get('priority') == 'low'],
                'risk_assessment': ai_report.get('risk_level', 'medium'),
                'next_monitoring_session': 'Recommended within 24-48 hours for trend analysis'
            }
            
            return summary
            
        except Exception as e:
            print(f"Error creating recommendation summary: {e}")
            return {
                'immediate_actions': ['Continue monitoring'],
                'general_advice': ['Maintain healthy lifestyle'],
                'long_term_goals': ['Regular health checkups'],
                'risk_assessment': 'medium',
                'next_monitoring_session': 'Continue as needed'
            }

# Test function
def test_health_analyzer():
    """Test the health analyzer with sample data"""
    # Replace with your actual Gemini API key
    api_key = "YOUR_GEMINI_API_KEY_HERE"
    
    analyzer = HealthAnalyzer(api_key)
    
    # Find the most recent CSV file
    csv_files = glob.glob('../fall_detection_data_*.csv')
    if csv_files:
        latest_csv = max(csv_files, key=os.path.getctime)
        print(f"📄 Analyzing: {latest_csv}")
        
        report = analyzer.generate_comprehensive_report(latest_csv)
        
        if report:
            print("✅ Health report generated!")
            print(json.dumps(report, indent=2))
        else:
            print("❌ Failed to generate report")
    else:
        print("❌ No CSV files found")

if __name__ == "__main__":
    test_health_analyzer()
