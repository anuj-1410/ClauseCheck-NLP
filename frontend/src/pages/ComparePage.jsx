import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { IconFile, IconSearch, IconArrowLeft, IconScale, IconCheck, IconX, IconAmbiguity } from '../components/Icons';

const API_URL = 'http://localhost:8000';

export default function ComparePage() {
    const [file1, setFile1] = useState(null);
    const [file2, setFile2] = useState(null);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const ref1 = useRef(null);
    const ref2 = useRef(null);
    const navigate = useNavigate();

    const handleCompare = async () => {
        if (!file1 || !file2) { setError('Please upload both documents.'); return; }
        setError('');
        setLoading(true);

        try {
            const formData = new FormData();
            formData.append('file1', file1);
            formData.append('file2', file2);

            const res = await fetch(`${API_URL}/api/compare`, {
                method: 'POST',
                body: formData,
            });

            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.detail || 'Comparison failed');
            }

            setResult(await res.json());
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const formatDelta = (val) => {
        if (val > 0) return { text: `+${val}`, cls: 'positive' };
        if (val < 0) return { text: `${val}`, cls: 'negative' };
        return { text: '0', cls: 'neutral' };
    };

    return (
        <div className="page">
            <div className="container">
                <div className="history-header animate-in">
                    <h1 className="history-title">Contract Comparison</h1>
                    <button className="btn btn-secondary" onClick={() => navigate('/')}><IconArrowLeft size={14} /> Back</button>
                </div>

                <p style={{ color: 'var(--text-muted)', marginBottom: 24, fontSize: '0.92rem' }}>
                    Upload two versions of a contract to see exactly what changed — clause by clause.
                </p>

                {/* Upload Zones */}
                <div className="compare-uploads animate-slide-up delay-1">
                    <div className={`compare-upload-zone ${file1 ? 'has-file' : ''}`} onClick={() => ref1.current?.click()}>
                        <div className="compare-icon"><IconFile size={32} /></div>
                        <p style={{ fontWeight: 600 }}>{file1 ? file1.name : 'Document 1 (Original)'}</p>
                        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4 }}>{file1 ? `${(file1.size / 1024).toFixed(0)} KB` : 'Click to upload'}</p>
                        <input ref={ref1} type="file" style={{ display: 'none' }} accept=".pdf,.docx,.txt" onChange={e => setFile1(e.target.files[0])} />
                    </div>
                    <div className={`compare-upload-zone ${file2 ? 'has-file' : ''}`} onClick={() => ref2.current?.click()}>
                        <div className="compare-icon"><IconFile size={32} /></div>
                        <p style={{ fontWeight: 600 }}>{file2 ? file2.name : 'Document 2 (Revised)'}</p>
                        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4 }}>{file2 ? `${(file2.size / 1024).toFixed(0)} KB` : 'Click to upload'}</p>
                        <input ref={ref2} type="file" style={{ display: 'none' }} accept=".pdf,.docx,.txt" onChange={e => setFile2(e.target.files[0])} />
                    </div>
                </div>

                <div style={{ textAlign: 'center', marginBottom: 32 }}>
                    <button className="btn btn-primary btn-lg" onClick={handleCompare} disabled={loading || !file1 || !file2}>
                        {loading ? 'Comparing...' : <><IconSearch size={16} /> Compare Documents</>}
                    </button>
                </div>

                {error && <div className="error-message" style={{ marginBottom: 20 }}>{error}</div>}

                {loading && (
                    <div style={{ textAlign: 'center', padding: 40 }}>
                        <div className="spinner" style={{ margin: '0 auto' }} />
                        <p style={{ marginTop: 16, color: 'var(--text-muted)' }}>Analyzing both documents...</p>
                    </div>
                )}

                {result && (
                    <div className="animate-in">
                        {/* Score Deltas */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 16, marginBottom: 24 }}>
                            <div className="glass-card card-3d" style={{ padding: 20, textAlign: 'center' }}>
                                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>Risk Score Change</div>
                                <div className={`delta-value ${formatDelta(result.risk_delta).cls}`}>{formatDelta(result.risk_delta).text}</div>
                                <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: 4, fontFamily: 'var(--mono)' }}>
                                    {result.document1?.risk_score} → {result.document2?.risk_score}
                                </div>
                            </div>
                            <div className="glass-card card-3d" style={{ padding: 20, textAlign: 'center' }}>
                                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>Compliance Change</div>
                                <div className={`delta-value ${formatDelta(result.compliance_delta).cls === 'positive' ? 'negative' : formatDelta(result.compliance_delta).cls === 'negative' ? 'positive' : 'neutral'}`}>{formatDelta(result.compliance_delta).text}</div>
                                <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: 4, fontFamily: 'var(--mono)' }}>
                                    {result.document1?.compliance_score} → {result.document2?.compliance_score}
                                </div>
                            </div>
                            <div className="glass-card card-3d" style={{ padding: 20, textAlign: 'center' }}>
                                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>Power Shift</div>
                                <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginTop: 8 }}>{result.power_shift}</div>
                            </div>
                        </div>

                        {/* Summary */}
                        <div className="glass-card" style={{ padding: 18, marginBottom: 24 }}>
                            <div className="markdown-body" style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}><ReactMarkdown>{result.summary}</ReactMarkdown></div>
                        </div>

                        {/* Changes */}
                        {result.added?.length > 0 && (
                            <div className="diff-section">
                                <div className="section-header"><h2>Added Clauses</h2><span className="section-badge">{result.added.length}</span></div>
                                {result.added.map((a, i) => (
                                    <div key={i} className="diff-item added"><p>{a.clause?.text?.slice(0, 300)}</p></div>
                                ))}
                            </div>
                        )}

                        {result.removed?.length > 0 && (
                            <div className="diff-section">
                                <div className="section-header"><h2>Removed Clauses</h2><span className="section-badge">{result.removed.length}</span></div>
                                {result.removed.map((r, i) => (
                                    <div key={i} className="diff-item removed"><p>{r.clause?.text?.slice(0, 300)}</p></div>
                                ))}
                            </div>
                        )}

                        {result.modified?.length > 0 && (
                            <div className="diff-section">
                                <div className="section-header"><h2>Modified Clauses</h2><span className="section-badge">{result.modified.length}</span></div>
                                {result.modified.map((m, i) => (
                                    <div key={i} className="diff-item modified" style={{ padding: 16 }}>
                                        <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginBottom: 6, fontFamily: 'var(--mono)' }}>Similarity: {Math.round(m.similarity * 100)}%</div>
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                                            <div>
                                                <div style={{ fontSize: '0.72rem', color: 'var(--risk-high)', fontWeight: 700, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Original</div>
                                                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{m.clause_doc1?.text?.slice(0, 200)}</p>
                                            </div>
                                            <div>
                                                <div style={{ fontSize: '0.72rem', color: 'var(--risk-low)', fontWeight: 700, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Revised</div>
                                                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{m.clause_doc2?.text?.slice(0, 200)}</p>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {result.unchanged?.length > 0 && (
                            <div style={{ marginTop: 16 }}>
                                <div className="section-header"><h2 style={{ color: 'var(--text-dim)' }}>Unchanged Clauses</h2><span className="section-badge">{result.unchanged.length}</span></div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
