import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const API_URL = 'http://localhost:8000';

const STEPS = [
    'Uploading document...',
    'Parsing content...',
    'Detecting language...',
    'Segmenting clauses...',
    'Extracting entities...',
    'Detecting obligations...',
    'Analyzing risks...',
    'Checking compliance...',
    'Detecting ambiguities...',
    'Extracting timeline...',
    'Generating explanations...',
    'Translating to plain English...',
    'Generating smart summary...',
    'Finalizing report...',
];

export default function UploadPage() {
    const [dragOver, setDragOver] = useState(false);
    const [processing, setProcessing] = useState(false);
    const [currentStep, setCurrentStep] = useState(0);
    const [error, setError] = useState('');
    const [jurisdiction, setJurisdiction] = useState('general');
    const [contractType, setContractType] = useState('general');
    const [options, setOptions] = useState(null);
    const inputRef = useRef(null);
    const navigate = useNavigate();

    useEffect(() => {
        fetch(`${API_URL}/api/options`)
            .then(r => r.json())
            .then(setOptions)
            .catch(() => { });
    }, []);

    const animateSteps = () => {
        let step = 0;
        const interval = setInterval(() => {
            step++;
            if (step < STEPS.length) setCurrentStep(step);
            else clearInterval(interval);
        }, 1200);
        return interval;
    };

    const handleFile = async (file) => {
        if (!file) return;
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!['.pdf', '.docx', '.txt'].includes(ext)) {
            setError('Unsupported file type. Please upload PDF, DOCX, or TXT files.');
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            setError('File too large. Maximum size is 10MB.');
            return;
        }

        setError('');
        setProcessing(true);
        setCurrentStep(0);
        const stepInterval = animateSteps();

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('jurisdiction', jurisdiction);
            formData.append('contract_type', contractType);

            const response = await fetch(`${API_URL}/api/analyze`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.detail || `Analysis failed (${response.status})`);
            }

            const result = await response.json();
            clearInterval(stepInterval);
            sessionStorage.setItem(`result_${result.id}`, JSON.stringify(result));
            navigate(`/results/${result.id}`);
        } catch (err) {
            clearInterval(stepInterval);
            setError(err.message || 'Analysis failed. Is the backend running?');
            setProcessing(false);
        }
    };

    const handleDrop = (e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); };
    const handleDragOver = (e) => { e.preventDefault(); setDragOver(true); };

    return (
        <>
            {processing && (
                <div className="processing-overlay">
                    <div className="spinner" />
                    <p className="processing-text">Analyzing your contract...</p>
                    <p className="processing-step">{STEPS[currentStep]}</p>
                </div>
            )}

            <div className="page">
                <div className="container">
                    <section className="hero-section animate-in">
                        <div className="hero-badge">
                            <span>🤖</span>
                            <span>AI-Powered Legal Intelligence Platform</span>
                        </div>
                        <h1 className="hero-title">
                            Analyze Legal Contracts<br />with Confidence
                        </h1>
                        <p className="hero-subtitle">
                            Upload your contract in English or Hindi. ClauseCheck detects risks,
                            checks compliance, explains every clause in plain language, and suggests
                            negotiation strategies — all with AI precision.
                        </p>

                        {/* Options Row */}
                        <div className="options-row animate-slide-up delay-1">
                            <div className="option-group">
                                <span className="option-label">Contract Type</span>
                                <select
                                    className="option-select"
                                    value={contractType}
                                    onChange={e => setContractType(e.target.value)}
                                >
                                    {(options?.contract_types || [
                                        { code: 'general', name: 'General Contract' },
                                        { code: 'employment', name: 'Employment Contract' },
                                        { code: 'nda', name: 'Non-Disclosure Agreement' },
                                        { code: 'service', name: 'Service Agreement' },
                                        { code: 'rental', name: 'Rental Agreement' },
                                        { code: 'freelance', name: 'Freelance/Consulting' },
                                    ]).map(t => (
                                        <option key={t.code} value={t.code}>{t.name}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="option-group">
                                <span className="option-label">Jurisdiction</span>
                                <select
                                    className="option-select"
                                    value={jurisdiction}
                                    onChange={e => setJurisdiction(e.target.value)}
                                >
                                    {(options?.jurisdictions || [
                                        { code: 'general', name: 'General / International' },
                                        { code: 'india', name: 'India' },
                                        { code: 'us', name: 'United States' },
                                        { code: 'uk', name: 'United Kingdom' },
                                    ]).map(j => (
                                        <option key={j.code} value={j.code}>{j.name}</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        <div
                            className={`upload-zone animate-slide-up delay-2 ${dragOver ? 'drag-over' : ''}`}
                            onClick={() => inputRef.current?.click()}
                            onDrop={handleDrop}
                            onDragOver={handleDragOver}
                            onDragLeave={() => setDragOver(false)}
                        >
                            <span className="upload-icon">📄</span>
                            <p className="upload-text">Drop your contract here or click to browse</p>
                            <p className="upload-subtext">Supports PDF, DOCX, TXT — up to 10MB</p>
                            <input
                                ref={inputRef} type="file" className="upload-input"
                                accept=".pdf,.docx,.txt" onChange={e => handleFile(e.target.files[0])}
                            />
                        </div>

                        {error && <div className="error-message" style={{ maxWidth: 600, margin: '20px auto' }}>{error}</div>}
                    </section>

                    <section className="features-grid">
                        {[
                            { icon: '🧠', title: 'Plain English', desc: 'Every clause translated into simple, everyday language using AI.' },
                            { icon: '🔍', title: 'Risk Detection', desc: 'Identifies unlimited liability, one-sided terms, and hidden traps.' },
                            { icon: '📊', title: 'Compliance Scoring', desc: 'Jurisdiction-aware checks with legal references and 0–100 score.' },
                            { icon: '🌐', title: 'Bilingual AI', desc: 'Analyzes contracts in English and Hindi with auto-detection.' },
                            { icon: '💬', title: 'Q&A Chatbot', desc: 'Ask anything about your contract and get instant, cited answers.' },
                            { icon: '📋', title: 'Contract Compare', desc: 'Upload two versions to see exactly what changed.' },
                            { icon: '⏱️', title: 'Timeline View', desc: 'Every deadline, notice period, and payment date visualized.' },
                            { icon: '🤝', title: 'Negotiation AI', desc: 'Get actionable advice on how to renegotiate risky clauses.' },
                            { icon: '📥', title: 'PDF Export', desc: 'Download professional reports to share with your team.' },
                            { icon: '🔮', title: 'What-If Analysis', desc: 'Modify clauses and predict the impact on risk.' },
                            { icon: '🕵️', title: 'Ambiguity Detection', desc: 'Flags passive voice, vague terms, and missing responsibilities.' },
                            { icon: '⚖️', title: 'Jurisdiction Aware', desc: 'Indian, US, UK, or international — law-specific analysis.' },
                        ].map((f, i) => (
                            <div key={i} className={`feature-card glass-card animate-slide-up delay-${(i % 5) + 1}`}>
                                <span className="feature-icon">{f.icon}</span>
                                <h3>{f.title}</h3>
                                <p>{f.desc}</p>
                            </div>
                        ))}
                    </section>
                </div>
            </div>
        </>
    );
}
