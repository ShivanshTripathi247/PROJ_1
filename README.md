# REAL‑TIME AI HEALTH MONITORING PLATFORM

## Overview

This project implements a real-time health and fall detection system based on Raspberry Pi, integrating multiple physiological sensors and machine learning to monitor vital signs and detect falls. The system combines edge embedded AI with cloud-powered language model analytics and GPS-enabled emergency alerts, providing a full-stack solution from data acquisition to actionable health insights and rapid response.

---

## Architecture

### Hardware Layer

- **Raspberry Pi**: Main edge computing device.
- **Sensors**:
  - **IMU (Triaxial Accelerometer + Gyroscope)**: Captures motion data for fall detection.
  - **MAX30102**: Optical pulse oximeter measuring heart rate (bpm) and blood oxygen (SpO2).
  - **NEO-6M GPS Module**: Provides geolocation for emergency alerting.
  
### Embedded Machine Learning

- **Fall Detection Model**: A Random Forest classifier processes IMU + heart rate data for real-time fall prediction on-device.
- **Data Pipeline**: Sensor data is stored and updated continuously in CSV format, facilitating live streaming and historical analytics.

### Backend Layer

- **Flask & Flask-SocketIO**: Provides REST APIs and bidirectional WebSocket streaming of sensor data and ML inference results.
- **Gemini LLM Integration**: Google's Gemini language model is integrated to generate AI-powered personalized health reports by analyzing sensor datasets.

### Frontend Layer

- **React Dashboard**: Displays real-time vitals, detected events, and live sensor graphs.
- **AI Health Reports**: Interactive report page displaying detailed AI-generated summaries, risk assessments, and actionable recommendations.
- **Emergency Alert Integration**: Alerts include GPS location sharing for rapid assistance during falls or critical health events.

---

## Features

- **Real-Time Monitoring** of heart rate, SpO2, triaxial acceleration, and gyroscope data.
- **Embedded ML-Based Fall Detection** utilizing Random Forest on combined sensor data.
- **AI-Powered Health Insights** with automated report generation leveraging Gemini LLM.
- **GPS-Enabled Emergency Alerts** with live location and Google Maps links.
- **Full-Stack Web Application** for seamless visualization and interaction.
- **Reliable Data Processing Pipeline** for continuous sensor reading and WebSocket broadcasting.

---

## Installation and Setup

1. **Hardware Wiring**: Connect sensors and GPS module to Raspberry Pi GPIO pins.
2. **Enable UART and Serial Interfaces** for GPS communication.
3. **Install Dependencies**:
   - Backend: Flask, Flask-SocketIO, pandas, google-generativeai, python-dotenv
   - Frontend: React, Chart.js, Socket.IO client, lucide-react icons
4. **Configure Gemini API Key** in backend `.env` file.
5. **Run Processes**:
   - Sensor data collection and fall detection process (`main.py`)
   - Backend Flask-SocketIO server (`app.py`)
   - React frontend dashboard (`npm start`)

---

## Usage

- Monitor live sensor readings and fall detection with real-time charts.
- Generate AI health reports from the latest data on-demand.
- Receive emergency notifications with precise location information when falls are detected.

---

## Future Enhancements

- Integration of SMS and email notification services for emergency alerts.
- Additional sensor fusion for enhanced anomaly detection.
- Cloud backend for persistent storage and longitudinal health analysis.
- Mobile app for health reporting and emergency response.
- Continuous model retraining with aggregated anonymized data for improved accuracy.

---
