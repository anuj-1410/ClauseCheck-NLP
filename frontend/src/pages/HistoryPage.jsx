import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Chart as ChartJS, ArcElement, Tooltip, Legend,
    CategoryScale, LinearScale, BarElement,
    RadialLinearScale, PointElement, LineElement, Filler,
} from 'chart.js';
import { Doughnut, Bar, Radar } from 'react-chartjs-2';

ChartJS.register(
    ArcElement, Tooltip, Legend,
    CategoryScale, LinearScale, BarElement,
    RadialLinearScale, PointElement, LineElement, Filler,
);

const API_URL = 'http://localhost:8000';

export default function HistoryPage() {
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        fetch(`${API_URL}/api/history`)
            .then(r => r.json())
            .then(data => setResults(data.results || []))
            .catch(err => setError(err.message))
            .finally(() => setLoading(false));
    }, []);

    // Charts
    const riskDistribution = {
        labels: ['Low (0-30)', 'Medium (31-60)', 'High (61-100)'],
        datasets: [{
            data: [
                results.filter(r => r.risk_score <= 30).length,
                results.filter(r => r.risk_score > 30 && r.risk_score <= 60).length,
                results.filter(r => r.risk_score > 60).length,
            ],
            backgroundColor: ['rgba(34, 197, 94, 0.6)', 'rgba(245, 158, 11, 0.6)', 'rgba(239, 68, 68, 0.6)'],
            borderColor: ['#22c55e', '#f59e0b', '#ef4444'],
            borderWidth: 2,
        }],
    };

    const complianceBar = {
        labels: results.slice(0, 8).map(r => r.document_name?.slice(0, 12) || 'Doc'),
        datasets: [{
            label: 'Compliance', data: results.slice(0, 8).map(r => r.compliance_score),
            backgroundColor: 'rgba(59, 130, 246, 0.5)', borderColor: '#3b82f6', borderWidth: 1, borderRadius: 6,
        }, {
            label: 'Risk', data: results.slice(0, 8).map(r => r.risk_score),
            backgroundColor: 'rgba(239, 68, 68, 0.4)', borderColor: '#ef4444', borderWidth: 1, borderRadius: 6,
        }],
    };

    const radarData = {
        labels: ['Risk Level', 'Compliance', 'Avg Score', 'Documents', 'Low Risk %'],
        datasets: [{
            label: 'Portfolio Health',
            data: [
                100 - (results.reduce((a, r) => a + r.risk_score, 0) / Math.max(results.length, 1)),
                results.reduce((a, r) => a + r.compliance_score, 0) / Math.max(results.length, 1),
                (results.reduce((a, r) => a + r.compliance_score - r.risk_score, 0) / Math.max(results.length, 1)) + 50,
                Math.min(results.length * 10, 100),
                (results.filter(r => r.risk_score <= 30).length / Math.max(results.length, 1)) * 100,
            ],
            backgroundColor: 'rgba(99, 102, 241, 0.15)',
            borderColor: '#6366f1', pointBackgroundColor: '#6366f1',
            pointBorderColor: '#fff', pointHoverRadius: 6, borderWidth: 2,
        }],
    };

    const chartOpts = { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color: '#94a3b8', font: { family: 'Inter' } } } }, scales: { x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.03)' } }, y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.03)' }, beginAtZero: true, max: 100 } } };
    const doughOpts = { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', padding: 14, font: { family: 'Inter' } } } } };
    const radarOpts = { responsive: true, maintainAspectRatio: true, plugins: { legend: { display: false } }, scales: { r: { ticks: { color: '#64748b', backdropColor: 'transparent' }, grid: { color: 'rgba(99,102,241,0.1)' }, pointLabels: { color: '#94a3b8', font: { size: 11, family: 'Inter' } }, suggestedMin: 0, suggestedMax: 100 } } };

    if (loading) return <div className="page"><div className="container" style={{ textAlign: 'center', paddingTop: 100 }}><div className="spinner" style={{ margin: '0 auto' }} /></div></div>;

    return (
        <div className="page">
            <div className="container">
                <div className="history-header animate-in">
                    <h1 className="history-title">Analysis History</h1>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <button className="btn btn-secondary" onClick={() => navigate('/compare')}>📋 Compare</button>
                        <button className="btn btn-primary" onClick={() => navigate('/')}>+ New Analysis</button>
                    </div>
                </div>

                {error && <div className="error-message">{error}</div>}

                {results.length > 0 && (
                    <div className="charts-grid animate-slide-up delay-1">
                        <div className="chart-card glass-card">
                            <h3>📊 Risk Distribution</h3>
                            <div style={{ maxWidth: 260, margin: '0 auto' }}><Doughnut data={riskDistribution} options={doughOpts} /></div>
                        </div>
                        <div className="chart-card glass-card">
                            <h3>📈 Score Comparison</h3>
                            <Bar data={complianceBar} options={chartOpts} />
                        </div>
                        <div className="chart-card glass-card">
                            <h3>🎯 Portfolio Health</h3>
                            <div style={{ maxWidth: 300, margin: '0 auto' }}><Radar data={radarData} options={radarOpts} /></div>
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
                        <button className="btn btn-primary" onClick={() => navigate('/')} style={{ marginTop: 20 }}>Analyze a Document</button>
                    </div>
                ) : (
                    <div className="history-list animate-slide-up delay-3">
                        {results.map(item => (
                            <div key={item.id} className="history-item glass-card" onClick={() => navigate(`/results/${item.id}`)}>
                                <div className="history-item-info">
                                    <div className="history-item-name">{item.document_name}</div>
                                    <div className="history-item-meta">
                                        <span>🌐 {item.language}</span>
                                        <span>📅 {new Date(item.created_at).toLocaleDateString()}</span>
                                    </div>
                                </div>
                                <div className="history-scores">
                                    <div className="mini-score risk">Risk: {item.risk_score}</div>
                                    <div className="mini-score compliance">Compliance: {item.compliance_score}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
