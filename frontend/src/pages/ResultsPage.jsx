import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ScoreGauge from '../components/ScoreGauge';
import ClauseCard from '../components/ClauseCard';

const API_URL = 'http://localhost:8000';

export default function ResultsPage() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [activeTab, setActiveTab] = useState('clauses');

    useEffect(() => {
        const loadResult = async () => {
            // Check sessionStorage first (from recent upload)
            const cached = sessionStorage.getItem(`result_${id}`);
            if (cached) {
                setResult(JSON.parse(cached));
                setLoading(false);
                return;
            }

            // Fetch from API
            try {
                const res = await fetch(`${API_URL}/api/history/${id}`);
                if (!res.ok) throw new Error('Result not found');
                const data = await res.json();
                setResult(data.result);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        loadResult();
    }, [id]);

    if (loading) {
        return (
            <div className="page">
                <div className="container" style={{ textAlign: 'center', paddingTop: '100px' }}>
                    <div className="spinner" style={{ margin: '0 auto' }} />
                    <p style={{ marginTop: 20, color: 'var(--text-muted)' }}>Loading results...</p>
                </div>
            </div>
        );
    }

    if (error || !result) {
        return (
            <div className="page">
                <div className="container">
                    <div className="error-message">
                        {error || 'Result not found.'}
                    </div>
                    <button className="btn btn-primary" onClick={() => navigate('/')} style={{ marginTop: 20 }}>
                        ← Analyze Another Document
                    </button>
                </div>
            </div>
        );
    }

    const { clause_analysis: ca } = result;
    const clauses = ca?.clauses || [];
    const entities = ca?.entities || {};
    const obligations = ca?.obligations || [];
    const risks = ca?.risks || [];
    const compliance = ca?.compliance || {};
    const explanations = ca?.explanations || {};
    const riskExplanations = explanations.risk_explanations || [];
    const complianceExplanations = explanations.compliance_explanations || [];
    const overallSummary = explanations.overall_summary || '';

    const riskColor = result.risk_score > 60 ? '#ef4444' : result.risk_score > 30 ? '#f59e0b' : '#22c55e';
    const complianceColor = result.compliance_score >= 70 ? '#22c55e' : result.compliance_score >= 40 ? '#f59e0b' : '#ef4444';

    const assessmentClass = result.risk_score > 60 ? 'danger' : result.risk_score > 30 ? 'warning' : 'safe';

    const entityCategories = [
        { key: 'parties', label: 'Parties', icon: '👤' },
        { key: 'dates', label: 'Dates', icon: '📅' },
        { key: 'monetary_values', label: 'Monetary Values', icon: '💰' },
        { key: 'durations', label: 'Durations', icon: '⏱️' },
        { key: 'legal_references', label: 'Legal References', icon: '⚖️' },
    ];

    const tabs = [
        { id: 'clauses', label: 'Clauses', count: clauses.length },
        { id: 'entities', label: 'Entities', count: Object.values(entities).flat().length },
        { id: 'obligations', label: 'Obligations', count: obligations.length },
        { id: 'compliance', label: 'Compliance', count: compliance.total_checked || 0 },
    ];

    return (
        <div className="page">
            <div className="container">
                {/* Header */}
                <div className="results-header animate-in">
                    <div>
                        <h1 className="results-title">Analysis Report</h1>
                    </div>
                    <div className="results-meta">
                        <span className="meta-badge">📄 {result.document_name}</span>
                        <span className="meta-badge">🌐 {result.language}</span>
                        <button className="btn btn-secondary" onClick={() => navigate('/')}>
                            + New Analysis
                        </button>
                    </div>
                </div>

                {/* Score Gauges */}
                <div className="scores-grid">
                    <ScoreGauge score={result.risk_score} label="Risk Score" color={riskColor} />
                    <ScoreGauge score={result.compliance_score} label="Compliance Score" color={complianceColor} />
                </div>

                {/* Summary */}
                <div className="summary-section glass-card animate-slide-up delay-2">
                    <h3>📋 Document Summary</h3>
                    <p className="summary-text">{result.summary}</p>
                    {overallSummary && (
                        <div className={`overall-assessment ${assessmentClass}`}>
                            {overallSummary}
                        </div>
                    )}
                </div>

                {/* Tab Navigation */}
                <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
                    {tabs.map(tab => (
                        <button
                            key={tab.id}
                            className={`btn ${activeTab === tab.id ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setActiveTab(tab.id)}
                            style={{ fontSize: '0.85rem', padding: '8px 18px' }}
                        >
                            {tab.label}
                            <span className="section-badge" style={{ marginLeft: 6 }}>{tab.count}</span>
                        </button>
                    ))}
                </div>

                {/* Clauses Tab */}
                {activeTab === 'clauses' && (
                    <section className="animate-in">
                        <div className="section-header">
                            <h2>Clause Analysis</h2>
                            <span className="section-badge">{clauses.length} clauses</span>
                        </div>
                        <div className="clauses-list">
                            {clauses.map(clause => (
                                <ClauseCard
                                    key={clause.id}
                                    clause={clause}
                                    risks={risks}
                                    explanations={riskExplanations}
                                />
                            ))}
                        </div>
                    </section>
                )}

                {/* Entities Tab */}
                {activeTab === 'entities' && (
                    <section className="animate-in">
                        <div className="section-header">
                            <h2>Named Entities</h2>
                        </div>
                        <div className="entities-grid">
                            {entityCategories.map(cat => {
                                const items = entities[cat.key] || [];
                                if (items.length === 0) return null;
                                return (
                                    <div key={cat.key} className="entity-card glass-card">
                                        <h4>{cat.icon} {cat.label}</h4>
                                        <ul className="entity-list">
                                            {items.slice(0, 10).map((item, i) => (
                                                <li key={i}>{item.text}</li>
                                            ))}
                                            {items.length > 10 && (
                                                <li style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                                    +{items.length - 10} more
                                                </li>
                                            )}
                                        </ul>
                                    </div>
                                );
                            })}
                            {Object.values(entities).flat().length === 0 && (
                                <div className="empty-state">
                                    <p>No entities extracted.</p>
                                </div>
                            )}
                        </div>
                    </section>
                )}

                {/* Obligations Tab */}
                {activeTab === 'obligations' && (
                    <section className="animate-in">
                        <div className="section-header">
                            <h2>Obligations</h2>
                            <span className="section-badge">{obligations.length} found</span>
                        </div>
                        <div className="obligations-list">
                            {obligations.map((obl, i) => (
                                <div key={i} className="obligation-card glass-card">
                                    <div className="obligation-header">
                                        <span className={`obligation-strength ${obl.strength}`}>
                                            {obl.strength}
                                        </span>
                                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                            Clause #{obl.clause_id}
                                        </span>
                                    </div>
                                    <p className="obligation-text">{obl.text}</p>
                                    <div className="obligation-details">
                                        {obl.party && (
                                            <div className="obligation-detail">
                                                <span className="obligation-detail-label">Party: </span>
                                                <span className="obligation-detail-value">{obl.party}</span>
                                            </div>
                                        )}
                                        {obl.deadline && (
                                            <div className="obligation-detail">
                                                <span className="obligation-detail-label">Deadline: </span>
                                                <span className="obligation-detail-value">{obl.deadline}</span>
                                            </div>
                                        )}
                                        {obl.condition && (
                                            <div className="obligation-detail">
                                                <span className="obligation-detail-label">Condition: </span>
                                                <span className="obligation-detail-value">{obl.condition}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                            {obligations.length === 0 && (
                                <div className="empty-state">
                                    <p>No obligations detected.</p>
                                </div>
                            )}
                        </div>
                    </section>
                )}

                {/* Compliance Tab */}
                {activeTab === 'compliance' && (
                    <section className="animate-in">
                        <div className="section-header">
                            <h2>Compliance Checklist</h2>
                            <span className="section-badge">
                                {compliance.total_found || 0}/{compliance.total_checked || 0} found
                            </span>
                        </div>

                        <div className="compliance-grid">
                            {(compliance.details || []).map((item, i) => (
                                <div key={i} className="compliance-item">
                                    <div className={`compliance-check ${item.found ? 'found' : 'missing'}`}>
                                        {item.found ? '✓' : '✗'}
                                    </div>
                                    <div>
                                        <div className="compliance-label">
                                            {item.clause_type?.replace(/_/g, ' ')}
                                        </div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                                            {item.description}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Missing clause explanations */}
                        {complianceExplanations.length > 0 && (
                            <div style={{ marginTop: 24 }}>
                                <h3 style={{ fontSize: '1.1rem', marginBottom: 14, color: 'var(--text-secondary)' }}>
                                    Missing Clause Alerts
                                </h3>
                                {complianceExplanations.map((exp, i) => (
                                    <div
                                        key={i}
                                        className="explanation-panel"
                                        style={{
                                            marginBottom: 10,
                                            borderLeftColor: exp.importance === 'critical' ? 'var(--risk-high)' :
                                                exp.importance === 'important' ? 'var(--risk-medium)' : 'var(--text-muted)'
                                        }}
                                    >
                                        {exp.explanation}
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>
                )}
            </div>
        </div>
    );
}
