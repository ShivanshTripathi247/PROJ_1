import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import io from 'socket.io-client';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { MapPin, Navigation as NavigationIcon, Satellite, ExternalLink } from 'lucide-react';
import { Home, FileText, Activity, Heart, TrendingUp, Shield } from 'lucide-react';
import HealthReport from './components/HealthReport';
import './App.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const GPSLocationCard = ({ gpsData }) => {
  const getStatusClass = (status) => {
    switch(status) {
      case 'fixed': return 'fixed';
      case 'searching': return 'searching';
      case 'offline': return 'offline';
      case 'initializing': return 'initializing';
      default: return 'offline';
    }
  };

  const getEmergencyReadyStatus = () => {
    return gpsData.latitude && gpsData.longitude ? 'ready' : 'not-ready';
  };

  const generateMapsLink = () => {
    if (gpsData.latitude && gpsData.longitude) {
      return `https://maps.google.com/maps?q=${gpsData.latitude},${gpsData.longitude}`;
    }
    return null;
  };

  const formatCoordinate = (coord, decimals = 6) => {
    return coord ? coord.toFixed(decimals) : '----.------';
  };

  return (
    <div className={`reading-card gps-location ${getStatusClass(gpsData.gps_status)}`}>
      <div className="reading-header">
        <MapPin size={24} />
        <div className="reading-info">
          <h3>GPS Location</h3>
          <span className={`gps-status-indicator ${getStatusClass(gpsData.gps_status)}`}>
            <Satellite size={12} />
            {gpsData.gps_status || 'offline'}
          </span>
        </div>
      </div>
      
      <div className={`reading-value location-text ${!gpsData.latitude ? 'no-signal' : ''}`}>
        {gpsData.latitude && gpsData.longitude 
          ? (
            <div className="coordinate-display">
              <div className="coordinate-row">
                <span className="coordinate-label">Lat:</span>
                <span className="coordinate-value">{formatCoordinate(gpsData.latitude)}</span>
              </div>
              <div className="coordinate-row">
                <span className="coordinate-label">Lon:</span>
                <span className="coordinate-value">{formatCoordinate(gpsData.longitude)}</span>
              </div>
            </div>
          )
          : '---.----, ---.----'
        }
      </div>
      
      <div className="reading-unit">Latitude, Longitude</div>
      
      <div className="reading-trend">
        <div className={`emergency-ready ${getEmergencyReadyStatus()}`}>
          <NavigationIcon size={16} />
          <span>Emergency Ready: {gpsData.latitude ? 'Yes' : 'No'}</span>
          <div className="status-dot"></div>
        </div>
      </div>

      {/* Satellite count */}
      {gpsData.satellites !== undefined && (
        <div className="satellite-indicator">
          <Satellite size={12} />
          <span>{gpsData.satellites} satellites</span>
          <div className="satellite-bars">
            {[...Array(8)].map((_, i) => (
              <div 
                key={i} 
                className={`satellite-bar ${i < (gpsData.satellites || 0) ? 'active' : ''}`}
              />
            ))}
          </div>
        </div>
      )}

      {/* Maps link button */}
      {generateMapsLink() && (
        <a 
          href={generateMapsLink()} 
          target="_blank" 
          rel="noopener noreferrer"
          className="maps-link-btn"
        >
          <ExternalLink size={14} />
          View on Maps
        </a>
      )}
    </div>
  );
};

// Dashboard Component (Your main monitoring view)
const Dashboard = () => {
  const [currentData, setCurrentData] = useState({
    heart_rate: null,
    spo2: null,
    accel_magnitude: 0,
    gyro_magnitude: 0,
    fall_detected: false,
    fall_confidence: 0,
    temperature: 0,
    datetime: '--:--:--',
    device_status: 'offline'
  });
  
  const [gpsData, setGpsData] = useState({
    latitude: null,           // 51.5074
    longitude: null,          // -0.1278
    altitude: null,           // 35.5 (meters)
    gps_status: 'offline',    // 'fixed', 'searching', 'offline', 'initializing'
    satellites: 0,            // Number of satellites
    fix_quality: 0,           // GPS fix quality (0-8)
    speed: null,              // Speed in km/h
    course: null,             // Direction in degrees
    timestamp: null           // Last update timestamp
  });
  
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: []
  });
  
  const [isConnected, setIsConnected] = useState(false);
  const [connectionQuality, setConnectionQuality] = useState('good');
  const socketRef = useRef();
  
  useEffect(() => {
    // Connect to Flask backend
    socketRef.current = io('http://localhost:5000');
    
    socketRef.current.on('connect', () => {
      setIsConnected(true);
      setConnectionQuality('excellent');
      console.log('✅ Connected to health monitor backend');
    });
    
    socketRef.current.on('disconnect', () => {
      setIsConnected(false);
      setConnectionQuality('offline');
      console.log('❌ Disconnected from backend');
    });
    
    socketRef.current.on('sensor_update', (data) => {
      console.log('📡 Received sensor data:', data);
      setCurrentData(data);
      updateChartData(data);
    });
    
    // Handle connection errors
    socketRef.current.on('connect_error', () => {
      setConnectionQuality('poor');
    });
    
    return () => {
      socketRef.current.disconnect();
    };
  }, []);
  
  const updateChartData = (newData) => {
    setChartData(prevData => {
      const newLabels = [...(prevData.labels || []), newData.datetime];
      const hrData = [...(prevData.datasets[0]?.data || []), newData.heart_rate];
      const accelData = [...(prevData.datasets[1]?.data || []), newData.accel_magnitude];
      const gyroData = [...(prevData.datasets[2]?.data || []), newData.gyro_magnitude];

      // Keep only last 30 points for better performance
      const maxPoints = 30;
      if (newLabels.length > maxPoints) {
        newLabels.splice(0, newLabels.length - maxPoints);
        hrData.splice(0, hrData.length - maxPoints);
        accelData.splice(0, accelData.length - maxPoints);
        gyroData.splice(0, gyroData.length - maxPoints);
      }
      
      return {
        labels: newLabels,
        datasets: [
          {
            label: 'Heart Rate (BPM)',
            data: hrData,
            borderColor: 'rgb(255, 99, 132)',
            backgroundColor: 'rgba(255, 99, 132, 0.1)',
            tension: 0.4,
            fill: false,
            pointRadius: 3,
            pointHoverRadius: 5,
            borderWidth: 2
          },
          {
            label: 'Acceleration (g)',
            data: accelData,
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.1)',
            tension: 0.4,
            fill: false,
            yAxisID: 'y1',
            pointRadius: 2,
            pointHoverRadius: 4,
            borderWidth: 2
          },
          {
            label: 'Rotation (°/s)',
            data: gyroData,
            borderColor: 'rgb(153, 102, 255)',
            backgroundColor: 'rgba(153, 102, 255, 0.1)',
            tension: 0.4,
            fill: false,
            yAxisID: 'y2',
            pointRadius: 1,
            pointHoverRadius: 3,
            borderWidth: 1
          }
        ]
      };
    });
  };
  
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      title: {
        display: true,
        text: '📈 Real-time Health Monitoring',
        font: { size: 16, weight: 'bold' },
        color: '#333'
      },
      legend: {
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 20,
          font: { size: 12 }
        }
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Time',
          font: { weight: 'bold' }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        }
      },
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        title: {
          display: true,
          text: 'Heart Rate (BPM)',
          color: 'rgb(255, 99, 132)',
          font: { weight: 'bold' }
        },
        min: 0,
        max: 200,
        grid: {
          color: 'rgba(255, 99, 132, 0.1)'
        }
      },
      y1: {
        type: 'linear',
        display: true,
        position: 'right',
        title: {
          display: true,
          text: 'Acceleration (g)',
          color: 'rgb(75, 192, 192)',
          font: { weight: 'bold' }
        },
        min: 0,
        max: 3,
        grid: {
          drawOnChartArea: false,
          color: 'rgba(75, 192, 192, 0.1)'
        },
      },
      y2: {
        type: 'linear',
        display: false,
        position: 'right',
        min: 0,
        max: 500,
      }
    },
    animation: {
      duration: 300
    }
  };
  
  const getStatusColor = (status) => {
    switch(status) {
      case 'online': return '#4CAF50';
      case 'offline': return '#f44336';
      default: return '#FF9800';
    }
  };

  const getConnectionQualityIcon = (quality) => {
    switch(quality) {
      case 'excellent': return '🟢';
      case 'good': return '🟡';
      case 'poor': return '🟠';
      case 'offline': return '🔴';
      default: return '⚫';
    }
  };

  const getActivityLevelText = (accel) => {
    if (accel < 0.9) return 'Resting';
    if (accel < 1.2) return 'Light Activity';
    if (accel < 1.8) return 'Moderate Activity';
    return 'High Activity';
  };

  const getHeartRateZone = (hr) => {
    if (!hr || hr <= 0) return 'No Data';
    if (hr < 60) return 'Low';
    if (hr <= 100) return 'Normal';
    if (hr <= 150) return 'Elevated';
    return 'High';
  };

  return (
    <div className="dashboard">
      {/* Status Bar */}
      <div className="status-bar">
        <div className="status-item">
          <span className="status-label">Connection:</span>
          <span className={`status-value ${connectionQuality}`}>
            {getConnectionQualityIcon(connectionQuality)} {connectionQuality.toUpperCase()}
          </span>
        </div>
        <div className="status-item">
          <span className="status-label">Device:</span>
          <span className="status-value" style={{color: getStatusColor(currentData.device_status)}}>
            {currentData.device_status === 'online' ? '✅ Online' : '⚠️ Offline'}
          </span>
        </div>
        <div className="status-item">
          <span className="status-label">Last Update:</span>
          <span className="status-value">{currentData.datetime}</span>
        </div>
      </div>

      {/* Main Readings Grid */}
      <div className="readings-grid">
        <div className="reading-card heart-rate">
          <div className="reading-header">
            <Heart size={24} />
            <div className="reading-info">
              <h3>Heart Rate</h3>
              <span className="reading-zone">{getHeartRateZone(currentData.heart_rate)}</span>
            </div>
          </div>
          <div className="reading-value">
            {currentData.heart_rate ? `${currentData.heart_rate}` : '--'}
          </div>
          <div className="reading-unit">BPM</div>
          <div className="reading-trend">
            <TrendingUp size={16} />
            <span>Normal Range: 60-100</span>
          </div>
        </div>
        
        <div className="reading-card spo2">
          <div className="reading-header">
            <Activity size={24} />
            <div className="reading-info">
              <h3>SpO2</h3>
              <span className="reading-zone">
                {currentData.spo2 ? (currentData.spo2 >= 95 ? 'Normal' : 'Low') : 'No Data'}
              </span>
            </div>
          </div>
          <div className="reading-value">
            {currentData.spo2 ? `${currentData.spo2}` : '--'}
          </div>
          <div className="reading-unit">%</div>
          <div className="reading-trend">
            <TrendingUp size={16} />
            <span>Normal: &gt;95%</span>
          </div>
        </div>
        
        <div className="reading-card movement">
          <div className="reading-header">
            <Activity size={24} />
            <div className="reading-info">
              <h3>Movement</h3>
              <span className="reading-zone">{getActivityLevelText(currentData.accel_magnitude)}</span>
            </div>
          </div>
          <div className="reading-value">
            {currentData.accel_magnitude?.toFixed(2) || '0.00'}
          </div>
          <div className="reading-unit">g</div>
          <div className="reading-trend">
            <TrendingUp size={16} />
            <span>Rotation: {currentData.gyro_magnitude?.toFixed(1) || '0.0'}°/s</span>
          </div>
        </div>
        
        <div className={`reading-card fall-status ${currentData.fall_detected ? 'alert' : 'safe'}`}>
          <div className="reading-header">
            <Shield size={24} />
            <div className="reading-info">
              <h3>Fall Detection</h3>
              <span className="reading-zone">
                {currentData.fall_detected ? 'ALERT' : 'Monitoring'}
              </span>
            </div>
          </div>
          <div className="reading-value status-text">
            {currentData.fall_detected ? 'FALL!' : 'Safe'}
          </div>
          <div className="reading-unit">
            {(currentData.fall_confidence * 100).toFixed(0)}% confidence
          </div>
          <div className="reading-trend">
            <Shield size={16} />
            <span>AI Monitoring Active</span>
          </div>
        </div>
        <GPSLocationCard gpsData={gpsData} />
      </div>
      
      {/* Real-time Chart */}
      <div className="chart-section">
        <div className="chart-container">
          <Line data={chartData} options={chartOptions} />
        </div>
      </div>
      
      {/* Additional Info Cards */}
      <div className="info-grid">
        <div className="info-card temperature">
          <div className="info-header">
            <span className="info-icon">🌡️</span>
            <h4>System Temperature</h4>
          </div>
          <p className="info-value">{currentData.temperature?.toFixed(1) || '--'}°C</p>
          <span className="info-status">{currentData.temperature > 50 ? 'Warm' : 'Normal'}</span>
        </div>
        
        <div className="info-card session">
          <div className="info-header">
            <span className="info-icon">⏱️</span>
            <h4>Session Status</h4>
          </div>
          <p className="info-value">Active</p>
          <span className="info-status">Real-time monitoring</span>
        </div>
        
        <div className="info-card data-quality">
          <div className="info-header">
            <span className="info-icon">📊</span>
            <h4>Data Quality</h4>
          </div>
          <p className="info-value">{isConnected ? 'Excellent' : 'Poor'}</p>
          <span className="info-status">
            {isConnected ? 'All sensors active' : 'Connection issues'}
          </span>
        </div>
      </div>
    </div>
  );
};

// Main Navigation Component
const MainNavigation = () => {
  const location = useLocation();
  
  return (
    <nav className="main-nav">
      <div className="nav-content">
        <div className="nav-brand">
          <span className="brand-icon">🏥</span>
          <h1>Health Monitor</h1>
          <span className="brand-subtitle">AI-Powered Healthcare</span>
        </div>
        <div className="nav-links">
          <Link 
            to="/" 
            className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
          >
            <Home size={20} />
            <span>Live Dashboard</span>
          </Link>
          <Link 
            to="/reports" 
            className={`nav-link ${location.pathname === '/reports' ? 'active' : ''}`}
          >
            <FileText size={20} />
            <span>AI Reports</span>
          </Link>
        </div>
      </div>
    </nav>
  );
};

// Main App Component
function App() {
  return (
    <Router>
      <div className="App">
        <MainNavigation />
        
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/reports" element={<HealthReport />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
