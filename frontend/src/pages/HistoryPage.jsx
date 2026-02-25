import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement } from 'chart.js';
import { Doughnut, Bar } from 'react-chartjs-2';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement);

const API_URL = 'http://localhost:8000';

export default function HistoryPage() {
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        fetchHistory();
    }, []);

    const fetchHistory = async () => {
        try {
            const res = await fetch(`${API_URL}/api/history`);
            if (!res.ok) throw new Error('Failed to fetch history');
            const data = await res.json();
            setResults(data.results || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Chart data
    const riskDistribution = {
        labels: ['Low Risk (0-30)', 'Medium Risk (31-60)', 'High Risk (61-100)'],
        datasets: [{
            data: [
                results.filter(r => r.risk_score <= 30).length,
                results.filter(r => r.risk_score > 30 && r.risk_score <= 60).length,
                results.filter(r => r.risk_score > 60).length,
            ],
            backgroundColor: ['rgba(34, 197, 94, 0.7)', 'rgba(245, 158, 11, 0.7)', 'rgba(239, 68, 68, 0.7)'],
            borderColor: ['#22c55e', '#f59e0b', '#ef4444'],
            borderWidth: 2,
        }],
    };

    const complianceScores = {
        labels: results.slice(0, 10).map(r => r.document_name?.slice(0, 15) || 'Doc'),
        datasets: [{
            label: 'Compliance Score',
            data: results.slice(0, 10).map(r => r.compliance_score),
            backgroundColor: 'rgba(59, 130, 246, 0.6)',
            borderColor: '#3b82f6',
            borderWidth: 1,
            borderRadius: 6,
        }],
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                labels: { color: '#94a3b8', font: { family: 'Inter' } }
            }
        },
        scales: {
            x: {
                ticks: { color: '#64748b' },
                grid: { color: 'rgba(255,255,255,0.04)' }
            },
            y: {
                ticks: { color: '#64748b' },
                grid: { color: 'rgba(255,255,255,0.04)' },
                beginAtZero: true,
                max: 100,
            }
        }
    };

    const doughnutOptions = {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                position: 'bottom',
                labels: { color: '#94a3b8', font: { family: 'Inter' }, padding: 16 }
            }
        }
    };

    if (loading) {
        return (
            <div className="page">
                <div className="container" style={{ textAlign: 'center', paddingTop: '100px' }}>
                    <div className="spinner" style={{ margin: '0 auto' }} />
                    <p style={{ marginTop: 20, color: 'var(--text-muted)' }}>Loading history...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="page">
            <div className="container">
                <div className="history-header animate-in">
                    <h1 className="history-title">Analysis History</h1>
                    <button className="btn btn-primary" onClick={() => navigate('/')}>
                        + New Analysis
                    </button>
                </div>

                {error && <div className="error-message">{error}</div>}

                {results.length > 0 && (
                    <div className="charts-grid animate-slide-up delay-1">
                        <div className="chart-card glass-card">
                            <h3>📊 Risk Distribution</h3>
                            <div style={{ maxWidth: 280, margin: '0 auto' }}>
                                <Doughnut data={riskDistribution} options={doughnutOptions} />
                            </div>
                        </div>
                        <div className="chart-card glass-card">
                            <h3>📈 Compliance Scores (Recent)</h3>
                            <Bar data={complianceScores} options={chartOptions} />
                        </div>
                    </div>
                )}

                <div className="section-header animate-slide-up delay-2">
                    <h2>Past Analyses</h2>
                    <span className="section-badge">{results.length} documents</span>
                </div>

                {results.length === 0 ? (
                    <div className="empty-state glass-card">
                        <div className="empty-state-icon">📋</div>
                        <p>No analyses yet. Upload a document to get started!</p>
                        <button className="btn btn-primary" onClick={() => navigate('/')} style={{ marginTop: 20 }}>
                            Analyze a Document
                        </button>
                    </div>
                ) : (
                    <div className="history-list animate-slide-up delay-3">
                        {results.map((item) => (
                            <div
                                key={item.id}
                                className="history-item glass-card"
                                onClick={() => navigate(`/results/${item.id}`)}
                            >
                                <div className="history-item-info">
                                    <div className="history-item-name">{item.document_name}</div>
                                    <div className="history-item-meta">
                                        <span>🌐 {item.language}</span>
                                        <span>📅 {new Date(item.created_at).toLocaleDateString()}</span>
                                    </div>
                                </div>
                                <div className="history-scores">
                                    <div className="mini-score risk">
                                        Risk: {item.risk_score}
                                    </div>
                                    <div className="mini-score compliance">
                                        Compliance: {item.compliance_score}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
