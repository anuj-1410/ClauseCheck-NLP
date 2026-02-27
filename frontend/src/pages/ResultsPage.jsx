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
    const [whatIfClause, setWhatIfClause] = useState(null);
    const [whatIfText, setWhatIfText] = useState('');
    const [whatIfResult, setWhatIfResult] = useState('');
    const [whatIfLoading, setWhatIfLoading] = useState(false);
    const [negotiateLoading, setNegotiateLoading] = useState({});
    const [negotiations, setNegotiations] = useState({});

    useEffect(() => {
        const loadResult = async () => {
            const cached = sessionStorage.getItem(`result_${id}`);
            if (cached) { setResult(JSON.parse(cached)); setLoading(false); return; }
            try {
                const res = await fetch(`${API_URL}/api/history/${id}`);
                if (!res.ok) throw new Error('Result not found');
                const data = await res.json();
                setResult(data.result);
            } catch (err) { setError(err.message); }
            finally { setLoading(false); }
        };
        loadResult();
    }, [id]);

    const handleWhatIf = async () => {
        if (!whatIfClause || !whatIfText.trim()) return;
        setWhatIfLoading(true);
        try {
            const res = await fetch(`${API_URL}/api/whatif`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ original_clause: whatIfClause.text, modified_clause: whatIfText }),
            });
            const data = await res.json();
            setWhatIfResult(data.analysis || 'Analysis unavailable');
        } catch { setWhatIfResult('Failed to get analysis. Check if GROQ_API_KEY is configured.'); }
        finally { setWhatIfLoading(false); }
    };

    const handleNegotiate = async (risk) => {
        const key = `${risk.clause_id}_${risk.risk_type}`;
        setNegotiateLoading(prev => ({ ...prev, [key]: true }));
        try {
            const res = await fetch(`${API_URL}/api/negotiate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    clause_text: risk.clause_text, risk_type: risk.risk_type, severity: risk.severity,
                }),
            });
            const data = await res.json();
            setNegotiations(prev => ({ ...prev, [key]: data.advice || 'Advice unavailable' }));
        } catch { setNegotiations(prev => ({ ...prev, [key]: 'Failed. Check GROQ_API_KEY.' })); }
        finally { setNegotiateLoading(prev => ({ ...prev, [key]: false })); }
    };

    if (loading) return <div className="page"><div className="container" style={{ textAlign: 'center', paddingTop: 100 }}><div className="spinner" style={{ margin: '0 auto' }} /><p style={{ marginTop: 20, color: 'var(--text-muted)' }}>Loading results...</p></div></div>;
    if (error || !result) return <div className="page"><div className="container"><div className="error-message">{error || 'Not found.'}</div><button className="btn btn-primary" onClick={() => navigate('/')} style={{ marginTop: 20 }}>← Analyze Another</button></div></div>;

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
    const responsibility = ca?.responsibility || {};
    const timeline = ca?.timeline || {};
    const plainEnglish = ca?.plain_english || [];
    const jurisdictionInfo = ca?.jurisdiction || {};
    const contractTypeInfo = ca?.contract_type || {};

    const riskColor = result.risk_score > 60 ? '#ef4444' : result.risk_score > 30 ? '#f59e0b' : '#22c55e';
    const complianceColor = result.compliance_score >= 70 ? '#22c55e' : result.compliance_score >= 40 ? '#f59e0b' : '#ef4444';
    const assessmentClass = result.risk_score > 60 ? 'danger' : result.risk_score > 30 ? 'warning' : 'safe';

    const tabs = [
        { id: 'clauses', label: '📝 Clauses', count: clauses.length },
        { id: 'plain', label: '💡 Plain English', count: plainEnglish.length },
        { id: 'risks', label: '🔍 Risks', count: risks.length },
        { id: 'responsibility', label: '🕵️ Ambiguity', count: responsibility.total_issues || 0 },
        { id: 'timeline', label: '⏱️ Timeline', count: timeline.total_events || 0 },
        { id: 'entities', label: '👤 Entities', count: Object.values(entities).flat().length },
        { id: 'obligations', label: '📌 Obligations', count: obligations.length },
        { id: 'compliance', label: '✅ Compliance', count: compliance.total_checked || 0 },
        { id: 'whatif', label: '🔮 What-If' },
    ];

    const entityCats = [
        { key: 'parties', label: 'Parties', icon: '👤' },
        { key: 'dates', label: 'Dates', icon: '📅' },
        { key: 'monetary_values', label: 'Monetary Values', icon: '💰' },
        { key: 'durations', label: 'Durations', icon: '⏱️' },
        { key: 'legal_references', label: 'Legal References', icon: '⚖️' },
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
                        {jurisdictionInfo.name && <span className="meta-badge">⚖️ {jurisdictionInfo.name}</span>}
                        {contractTypeInfo.name && <span className="meta-badge">📋 {contractTypeInfo.name}</span>}
                        <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/chat/${id}`)}>💬 Chat</button>
                        <a className="btn btn-secondary btn-sm" href={`${API_URL}/api/report/${id}`} target="_blank" rel="noreferrer">📥 PDF</a>
                        <button className="btn btn-primary btn-sm" onClick={() => navigate('/')}>+ New</button>
                    </div>
                </div>

                {/* Scores */}
                <div className="scores-grid">
                    <ScoreGauge score={result.risk_score} label="Risk Score" color={riskColor} />
                    <ScoreGauge score={result.compliance_score} label="Compliance Score" color={complianceColor} />
                    {responsibility.ambiguity_score !== undefined && (
                        <ScoreGauge score={responsibility.ambiguity_score} label="Ambiguity Score" color={responsibility.ambiguity_score > 50 ? '#f59e0b' : '#22c55e'} />
                    )}
                </div>

                {/* Summary */}
                <div className="summary-section glass-card animate-slide-up delay-2">
                    <h3>📋 Executive Summary</h3>
                    <p className="summary-text">{result.summary}</p>
                    {overallSummary && <div className={`overall-assessment ${assessmentClass}`}>{overallSummary}</div>}
                </div>

                {/* Tabs */}
                <div className="tabs-container">
                    {tabs.map(tab => (
                        <button key={tab.id} className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`} onClick={() => setActiveTab(tab.id)}>
                            {tab.label}
                            {tab.count !== undefined && <span className="tab-count">{tab.count}</span>}
                        </button>
                    ))}
                </div>

                {/* CLAUSES TAB */}
                {activeTab === 'clauses' && (
                    <section className="animate-in">
                        <div className="section-header"><h2>Clause Analysis</h2><span className="section-badge">{clauses.length} clauses</span></div>
                        <div className="clauses-list">
                            {clauses.map(clause => <ClauseCard key={clause.id} clause={clause} risks={risks} explanations={riskExplanations} />)}
                        </div>
                    </section>
                )}

                {/* PLAIN ENGLISH TAB */}
                {activeTab === 'plain' && (
                    <section className="animate-in">
                        <div className="section-header"><h2>Plain English Breakdown</h2><span className="section-badge">{plainEnglish.length} translated</span></div>
                        {plainEnglish.length === 0 ? (
                            <div className="empty-state glass-card"><div className="empty-state-icon">💡</div><p>Plain English translations require a GROQ_API_KEY configured in the backend.</p></div>
                        ) : (
                            <div className="plain-english-list">
                                {plainEnglish.map((pe, i) => (
                                    <div key={i} className="plain-english-card glass-card animate-slide-up" style={{ animationDelay: `${i * 0.05}s` }}>
                                        <div className="clause-id" style={{ marginBottom: 10, display: 'inline-block' }}>Clause #{pe.clause_id}</div>
                                        <div className="original">{pe.original}</div>
                                        <span className="arrow">↓ Simplified</span>
                                        <div className="simplified">{pe.simplified}</div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>
                )}

                {/* RISKS TAB + NEGOTIATION */}
                {activeTab === 'risks' && (
                    <section className="animate-in">
                        <div className="section-header"><h2>Risk Findings</h2><span className="section-badge">{risks.length} found</span></div>
                        {risks.map((risk, i) => {
                            const key = `${risk.clause_id}_${risk.risk_type}`;
                            return (
                                <div key={i} className="glass-card" style={{ marginBottom: 10, padding: 18 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                                        <span className={`risk-badge ${risk.severity}`}>{risk.severity === 'high' ? '🔴' : risk.severity === 'medium' ? '🟡' : '🟢'} {risk.severity}</span>
                                        <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{risk.risk_type?.replace(/_/g, ' ')}</span>
                                        <span className="confidence-badge">🎯 {Math.round((risk.confidence || 0.7) * 100)}%</span>
                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>Clause #{risk.clause_id}</span>
                                    </div>
                                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{risk.description}</p>
                                    {risk.legal_note && <p style={{ fontSize: '0.78rem', color: 'var(--accent-amber)', marginTop: 6 }}>⚖️ {risk.legal_note}</p>}
                                    <div style={{ marginTop: 10 }}>
                                        {negotiations[key] ? (
                                            <div className="negotiation-advice">{negotiations[key]}</div>
                                        ) : (
                                            <button className="btn btn-secondary btn-sm" onClick={() => handleNegotiate(risk)} disabled={negotiateLoading[key]}>
                                                {negotiateLoading[key] ? '⏳ Analyzing...' : '🤝 Get Negotiation Advice'}
                                            </button>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                        {risks.length === 0 && <div className="empty-state glass-card"><div className="empty-state-icon">✅</div><p>No risks detected!</p></div>}
                    </section>
                )}

                {/* RESPONSIBILITY / AMBIGUITY TAB */}
                {activeTab === 'responsibility' && (
                    <section className="animate-in">
                        <div className="section-header"><h2>Responsibility & Ambiguity</h2><span className="section-badge">{responsibility.total_issues || 0} issues</span></div>
                        {(responsibility.passive_voice || []).length > 0 && (<><h3 style={{ fontSize: '0.95rem', margin: '16px 0 10px', color: 'var(--risk-high)' }}>🔴 Passive Voice ({responsibility.passive_voice.length})</h3>
                            <div className="responsibility-list">{responsibility.passive_voice.map((pv, i) => (
                                <div key={i} className="responsibility-item passive"><div className="issue-type" style={{ color: 'var(--risk-high)' }}>Passive Voice — Clause #{pv.clause_id}</div><p>{pv.issue}</p><p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginTop: 4 }}>Matched: "{pv.matched_text}"</p><p style={{ color: 'var(--accent-emerald)', fontSize: '0.8rem', marginTop: 4 }}>💡 {pv.suggestion}</p></div>
                            ))}</div></>)}
                        {(responsibility.vague_terms || []).length > 0 && (<><h3 style={{ fontSize: '0.95rem', margin: '16px 0 10px', color: 'var(--accent-amber)' }}>🟡 Vague Terms ({responsibility.vague_terms.length})</h3>
                            <div className="responsibility-list">{responsibility.vague_terms.map((vt, i) => (
                                <div key={i} className="responsibility-item vague"><div className="issue-type" style={{ color: 'var(--accent-amber)' }}>Vague Term — Clause #{vt.clause_id}</div><p>{vt.issue}</p><p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginTop: 4 }}>Context: {vt.context}</p></div>
                            ))}</div></>)}
                        {(responsibility.missing_subjects || []).length > 0 && (<><h3 style={{ fontSize: '0.95rem', margin: '16px 0 10px', color: 'var(--accent-purple)' }}>🟣 Missing Subjects ({responsibility.missing_subjects.length})</h3>
                            <div className="responsibility-list">{responsibility.missing_subjects.map((ms, i) => (
                                <div key={i} className="responsibility-item missing"><div className="issue-type" style={{ color: 'var(--accent-purple)' }}>Missing Subject — Clause #{ms.clause_id}</div><p>{ms.issue}</p></div>
                            ))}</div></>)}
                        {(responsibility.total_issues || 0) === 0 && <div className="empty-state glass-card"><div className="empty-state-icon">✅</div><p>No ambiguity issues detected.</p></div>}
                    </section>
                )}

                {/* TIMELINE TAB */}
                {activeTab === 'timeline' && (
                    <section className="animate-in">
                        <div className="section-header"><h2>Contract Timeline</h2><span className="section-badge">{timeline.total_events || 0} events</span></div>
                        {(timeline.events || []).length > 0 ? (
                            <div className="timeline-container">
                                {timeline.events.map((ev, i) => (
                                    <div key={i} className="timeline-event animate-slide-up" style={{ animationDelay: `${i * 0.06}s` }}>
                                        <div className="timeline-event-header">
                                            <span className="timeline-event-type" style={{ background: `${ev.category?.color || '#3b82f6'}20`, color: ev.category?.color || '#3b82f6' }}>
                                                {ev.category?.icon} {ev.type}
                                            </span>
                                            <span className="timeline-event-value">{ev.value}</span>
                                        </div>
                                        <p className="timeline-event-desc">{ev.description}</p>
                                        {ev.clause_id && <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>Clause #{ev.clause_id}</span>}
                                    </div>
                                ))}
                            </div>
                        ) : <div className="empty-state glass-card"><div className="empty-state-icon">📅</div><p>No timeline events found.</p></div>}
                    </section>
                )}

                {/* ENTITIES TAB */}
                {activeTab === 'entities' && (
                    <section className="animate-in">
                        <div className="section-header"><h2>Named Entities</h2></div>
                        <div className="entities-grid">
                            {entityCats.map(cat => {
                                const items = entities[cat.key] || [];
                                if (items.length === 0) return null;
                                return (<div key={cat.key} className="entity-card glass-card"><h4>{cat.icon} {cat.label}</h4><ul className="entity-list">{items.slice(0, 12).map((item, i) => <li key={i}>{item.text}</li>)}{items.length > 12 && <li style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>+{items.length - 12} more</li>}</ul></div>);
                            })}
                        </div>
                    </section>
                )}

                {/* OBLIGATIONS TAB */}
                {activeTab === 'obligations' && (
                    <section className="animate-in">
                        <div className="section-header"><h2>Obligations</h2><span className="section-badge">{obligations.length}</span></div>
                        <div className="obligations-list">
                            {obligations.map((obl, i) => (
                                <div key={i} className="obligation-card glass-card">
                                    <div className="obligation-header">
                                        <span className={`obligation-strength ${obl.strength}`}>{obl.strength}</span>
                                        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Clause #{obl.clause_id}</span>
                                    </div>
                                    <p className="obligation-text">{obl.text}</p>
                                    <div className="obligation-details">
                                        {obl.party && <div className="obligation-detail"><span className="obligation-detail-label">Party: </span><span className="obligation-detail-value">{obl.party}</span></div>}
                                        {obl.deadline && <div className="obligation-detail"><span className="obligation-detail-label">Deadline: </span><span className="obligation-detail-value">{obl.deadline}</span></div>}
                                        {obl.condition && <div className="obligation-detail"><span className="obligation-detail-label">Condition: </span><span className="obligation-detail-value">{obl.condition}</span></div>}
                                    </div>
                                </div>
                            ))}
                            {obligations.length === 0 && <div className="empty-state"><p>No obligations detected.</p></div>}
                        </div>
                    </section>
                )}

                {/* COMPLIANCE TAB */}
                {activeTab === 'compliance' && (
                    <section className="animate-in">
                        <div className="section-header"><h2>Compliance Checklist</h2><span className="section-badge">{compliance.total_found || 0}/{compliance.total_checked || 0}</span></div>
                        <div className="compliance-grid">
                            {(compliance.details || []).map((item, i) => (
                                <div key={i} className="compliance-item">
                                    <div className={`compliance-check ${item.found ? 'found' : 'missing'}`}>{item.found ? '✓' : '✗'}</div>
                                    <div style={{ flex: 1 }}>
                                        <div className="compliance-label">{item.clause_type?.replace(/_/g, ' ')}</div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>{item.description}</div>
                                        {item.legal_reference && <div style={{ fontSize: '0.72rem', color: 'var(--accent-amber)', marginTop: 2 }}>⚖️ {item.legal_reference}</div>}
                                    </div>
                                </div>
                            ))}
                        </div>
                        {complianceExplanations.length > 0 && (
                            <div style={{ marginTop: 24 }}>
                                <h3 style={{ fontSize: '1rem', marginBottom: 12, color: 'var(--text-secondary)' }}>Missing Clause Alerts</h3>
                                {complianceExplanations.map((exp, i) => (
                                    <div key={i} className="explanation-panel" style={{ marginBottom: 8, borderLeftColor: exp.importance === 'critical' ? 'var(--risk-high)' : 'var(--risk-medium)' }}>{exp.explanation}</div>
                                ))}
                            </div>
                        )}
                    </section>
                )}

                {/* WHAT-IF TAB */}
                {activeTab === 'whatif' && (
                    <section className="animate-in">
                        <div className="section-header"><h2>What-If Simulator</h2></div>
                        <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', marginBottom: 16 }}>Select a clause, modify it, and see how the risk profile changes.</p>
                        <div className="glass-card" style={{ padding: 20 }}>
                            <label style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: 8, display: 'block' }}>Select a clause to modify:</label>
                            <select className="option-select" style={{ width: '100%', marginBottom: 14 }} value={whatIfClause?.id || ''} onChange={(e) => {
                                const c = clauses.find(c => c.id === parseInt(e.target.value));
                                setWhatIfClause(c || null);
                                setWhatIfText(c?.text || '');
                                setWhatIfResult('');
                            }}>
                                <option value="">Choose a clause...</option>
                                {clauses.map(c => <option key={c.id} value={c.id}>Clause #{c.id}: {c.text.slice(0, 80)}...</option>)}
                            </select>
                            {whatIfClause && (
                                <div className="whatif-panel">
                                    <label style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6, display: 'block' }}>Original clause:</label>
                                    <div style={{ padding: 12, background: 'rgba(0,0,0,0.2)', borderRadius: 8, fontSize: '0.82rem', color: 'var(--text-dim)', marginBottom: 14 }}>{whatIfClause.text}</div>
                                    <label style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6, display: 'block' }}>Your modified version:</label>
                                    <textarea className="whatif-textarea" value={whatIfText} onChange={e => setWhatIfText(e.target.value)} placeholder="Edit the clause text..." />
                                    <button className="btn btn-primary" onClick={handleWhatIf} disabled={whatIfLoading} style={{ marginTop: 12 }}>
                                        {whatIfLoading ? '⏳ Analyzing...' : '🔮 Simulate Change'}
                                    </button>
                                    {whatIfResult && <div className="whatif-result">{whatIfResult}</div>}
                                </div>
                            )}
                        </div>
                    </section>
                )}
            </div>
        </div>
    );
}
