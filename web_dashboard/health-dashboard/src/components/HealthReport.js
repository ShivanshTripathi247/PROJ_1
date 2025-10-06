import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Heart, 
  Activity, 
  AlertTriangle, 
  CheckCircle, 
  Clock,
  TrendingUp,
  Shield,
  RefreshCw,
  Download,
  User,
  BarChart3
} from 'lucide-react';
import './HealthReport.css';

const HealthReport = () => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastGenerated, setLastGenerated] = useState(null);

  const generateReport = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:5000/api/generate-report');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const reportData = await response.json();
      setReport(reportData);
      setLastGenerated(new Date());
    } catch (err) {
      console.error('Error generating report:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDateTime = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const getRiskColor = (riskLevel) => {
    switch(riskLevel?.toLowerCase()) {
      case 'low': return '#4CAF50';
      case 'medium': return '#FF9800';
      case 'high': return '#f44336';
      default: return '#2196F3';
    }
  };

  const getRiskIcon = (riskLevel) => {
    switch(riskLevel?.toLowerCase()) {
      case 'low': return <CheckCircle color="#4CAF50" size={24} />;
      case 'medium': return <AlertTriangle color="#FF9800" size={24} />;
      case 'high': return <AlertTriangle color="#f44336" size={24} />;
      default: return <Shield color="#2196F3" size={24} />;
    }
  };

  const downloadReport = () => {
    if (!report) return;
    
    const reportText = JSON.stringify(report, null, 2);
    const blob = new Blob([reportText], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `health-report-${report.report_id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="health-report-container">
      <header className="report-header">
        <div className="header-content">
          <div className="header-info">
            <FileText size={32} />
            <div>
              <h1>🤖 AI Health Report</h1>
              <p>Powered by Gemini AI Analytics</p>
            </div>
          </div>
          <div className="header-actions">
            <button 
              onClick={generateReport} 
              disabled={loading}
              className="generate-btn"
            >
              <RefreshCw className={loading ? 'spinning' : ''} size={20} />
              {loading ? 'Generating...' : 'Generate Report'}
            </button>
            {report && (
              <button onClick={downloadReport} className="download-btn">
                <Download size={20} />
                Download
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="report-content">
        {error && (
          <div className="error-card">
            <AlertTriangle color="#f44336" size={24} />
            <div>
              <h3>Report Generation Failed</h3>
              <p>{error}</p>
              <button onClick={generateReport} className="retry-btn">
                Try Again
              </button>
            </div>
          </div>
        )}

        {loading && (
          <div className="loading-card">
            <div className="loading-spinner">
              <RefreshCw className="spinning" size={32} />
            </div>
            <h3>🤖 AI is analyzing your health data...</h3>
            <p>This may take a few moments</p>
          </div>
        )}

        {report && (
          <div className="report-sections">
            {/* Report Header Info */}
            <div className="report-info-card">
              <div className="info-grid">
                <div className="info-item">
                  <Clock size={20} />
                  <div>
                    <span className="label">Generated</span>
                    <span className="value">{formatDateTime(report.generated_at)}</span>
                  </div>
                </div>
                <div className="info-item">
                  <BarChart3 size={20} />
                  <div>
                    <span className="label">Session Duration</span>
                    <span className="value">{report.session_summary?.duration_minutes?.toFixed(1)} minutes</span>
                  </div>
                </div>
                <div className="info-item">
                  <Activity size={20} />
                  <div>
                    <span className="label">Data Points</span>
                    <span className="value">{report.session_summary?.total_samples}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Health Status Overview */}
            <div className="status-card">
              <div className="card-header">
                <User size={24} />
                <h2>Health Status Overview</h2>
              </div>
              <div className="status-content">
                <div className="risk-indicator">
                  {getRiskIcon(report.ai_insights?.risk_level)}
                  <div>
                    <h3>Risk Level: {report.ai_insights?.risk_level?.toUpperCase()}</h3>
                    <p className="status-description">
                      {report.ai_insights?.health_status}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Health Metrics */}
            <div className="metrics-grid">
              {/* Heart Rate Metrics */}
              <div className="metric-card">
                <div className="card-header">
                  <Heart size={24} color="#e91e63" />
                  <h3>Heart Rate Analysis</h3>
                </div>
                <div className="metric-content">
                  {report.health_metrics?.heart_rate?.status === 'analyzed' ? (
                    <>
                      <div className="metric-stats">
                        <div className="stat">
                          <span className="stat-label">Average</span>
                          <span className="stat-value">{report.health_metrics.heart_rate.average} BPM</span>
                        </div>
                        <div className="stat">
                          <span className="stat-label">Range</span>
                          <span className="stat-value">
                            {report.health_metrics.heart_rate.min} - {report.health_metrics.heart_rate.max} BPM
                          </span>
                        </div>
                        <div className="stat">
                          <span className="stat-label">Coverage</span>
                          <span className="stat-value">{report.health_metrics.heart_rate.coverage}%</span>
                        </div>
                      </div>
                      <div className="zones">
                        <h4>Heart Rate Zones</h4>
                        <div className="zone-bars">
                          <div className="zone-bar">
                            <span>Resting (&lt;70)</span>
                            <div className="bar">
                              <div className="fill resting" style={{width: '60%'}}></div>
                            </div>
                            <span>{report.health_metrics.heart_rate.zones?.resting || 0}</span>
                          </div>
                          <div className="zone-bar">
                            <span>Moderate (70-85)</span>
                            <div className="bar">
                              <div className="fill moderate" style={{width: '30%'}}></div>
                            </div>
                            <span>{report.health_metrics.heart_rate.zones?.moderate || 0}</span>
                          </div>
                          <div className="zone-bar">
                            <span>Elevated (&gt;85)</span>
                            <div className="bar">
                              <div className="fill elevated" style={{width: '10%'}}></div>
                            </div>
                            <span>{report.health_metrics.heart_rate.zones?.elevated || 0}</span>
                          </div>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="no-data">
                      <AlertTriangle color="#FF9800" size={20} />
                      <p>No heart rate data available in this session</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Movement Metrics */}
              <div className="metric-card">
                <div className="card-header">
                  <TrendingUp size={24} color="#4CAF50" />
                  <h3>Activity & Movement</h3>
                </div>
                <div className="metric-content">
                  <div className="metric-stats">
                    <div className="stat">
                      <span className="stat-label">Activity Level</span>
                      <span className="stat-value activity-level">
                        {report.health_metrics?.movement?.activity_level?.replace('_', ' ').toUpperCase()}
                      </span>
                    </div>
                    <div className="stat">
                      <span className="stat-label">Avg Acceleration</span>
                      <span className="stat-value">{report.health_metrics?.movement?.avg_acceleration}g</span>
                    </div>
                    <div className="stat">
                      <span className="stat-label">Max Movement</span>
                      <span className="stat-value">{report.health_metrics?.movement?.max_acceleration}g</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Fall Detection */}
              <div className="metric-card">
                <div className="card-header">
                  <Shield size={24} color="#2196F3" />
                  <h3>Fall Detection</h3>
                </div>
                <div className="metric-content">
                  <div className="fall-status">
                    {report.health_metrics?.fall_detection?.total_falls_detected === 0 ? (
                      <div className="no-falls">
                        <CheckCircle color="#4CAF50" size={32} />
                        <h4>No Falls Detected</h4>
                        <p>System monitored successfully</p>
                      </div>
                    ) : (
                      <div className="falls-detected">
                        <AlertTriangle color="#FF9800" size={32} />
                        <h4>{report.health_metrics.fall_detection.total_falls_detected} Fall Event(s)</h4>
                        <div className="fall-times">
                          {report.health_metrics.fall_detection.fall_timestamps?.map((time, index) => (
                            <span key={index} className="fall-time">{time}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* AI Insights */}
            <div className="insights-section">
              <div className="card-header">
                <FileText size={24} />
                <h2>🤖 AI Analysis & Insights</h2>
              </div>

              {/* Key Findings */}
              <div className="findings-card">
                <h3>Key Findings</h3>
                <ul className="findings-list">
                  {report.ai_insights?.key_findings?.map((finding, index) => (
                    <li key={index} className="finding-item">
                      <CheckCircle size={16} color="#4CAF50" />
                      {finding}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Recommendations */}
              <div className="recommendations-section">
                <h3>🎯 Personalized Recommendations</h3>
                <div className="recommendations-grid">
                  {report.ai_insights?.recommendations?.map((rec, index) => (
                    <div key={index} className={`recommendation-card ${rec.priority}`}>
                      <div className="rec-header">
                        <span className={`priority-badge ${rec.priority}`}>
                          {rec.priority?.toUpperCase()}
                        </span>
                        <span className="category">{rec.category?.toUpperCase()}</span>
                      </div>
                      <p className="rec-advice">{rec.advice}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Risk Factors */}
              {report.ai_insights?.risk_factors && (
                <div className="risk-factors-card">
                  <h3>⚠️ Risk Factors Identified</h3>
                  <ul className="risk-list">
                    {report.ai_insights.risk_factors.map((factor, index) => (
                      <li key={index} className="risk-item">
                        <AlertTriangle size={16} color="#FF9800" />
                        {factor}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Next Steps */}
              {report.ai_insights?.next_steps && (
                <div className="next-steps-card">
                  <h3>🚀 Recommended Next Steps</h3>
                  <ol className="steps-list">
                    {report.ai_insights.next_steps.map((step, index) => (
                      <li key={index} className="step-item">{step}</li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          </div>
        )}

        {!report && !loading && !error && (
          <div className="empty-state">
            <FileText size={64} color="#ccc" />
            <h3>No Report Generated Yet</h3>
            <p>Click "Generate Report" to create your AI-powered health analysis</p>
            <button onClick={generateReport} className="generate-btn large">
              <RefreshCw size={20} />
              Generate Your First Report
            </button>
          </div>
        )}
      </main>
    </div>
  );
};

export default HealthReport;
