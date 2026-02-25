import { useState, useRef } from 'react';
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
    'Generating explanations...',
    'Finalizing report...',
];

export default function UploadPage() {
    const [dragOver, setDragOver] = useState(false);
    const [processing, setProcessing] = useState(false);
    const [currentStep, setCurrentStep] = useState(0);
    const [error, setError] = useState('');
    const inputRef = useRef(null);
    const navigate = useNavigate();

    const animateSteps = () => {
        let step = 0;
        const interval = setInterval(() => {
            step++;
            if (step < STEPS.length) {
                setCurrentStep(step);
            } else {
                clearInterval(interval);
            }
        }, 1500);
        return interval;
    };

    const handleFile = async (file) => {
        if (!file) return;

        // Validate
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

            // Store result in sessionStorage for the results page
            sessionStorage.setItem(`result_${result.id}`, JSON.stringify(result));

            // Navigate to results
            navigate(`/results/${result.id}`);
        } catch (err) {
            clearInterval(stepInterval);
            setError(err.message || 'Analysis failed. Is the backend running?');
            setProcessing(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files[0];
        handleFile(file);
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        setDragOver(true);
    };

    const handleDragLeave = () => setDragOver(false);

    const handleInputChange = (e) => {
        const file = e.target.files[0];
        handleFile(file);
    };

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
                            <span>AI-Powered Legal Analysis</span>
                        </div>
                        <h1 className="hero-title">
                            Analyze Legal Contracts<br />with Confidence
                        </h1>
                        <p className="hero-subtitle">
                            Upload your contract in English or Hindi. ClauseCheck will detect risks,
                            check compliance, and explain every flagged clause — all while keeping
                            your document private.
                        </p>

                        <div
                            id="upload-dropzone"
                            className={`upload-zone animate-slide-up delay-2 ${dragOver ? 'drag-over' : ''}`}
                            onClick={() => inputRef.current?.click()}
                            onDrop={handleDrop}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                        >
                            <span className="upload-icon">📄</span>
                            <p className="upload-text">
                                Drop your contract here or click to browse
                            </p>
                            <p className="upload-subtext">
                                Supports PDF, DOCX, TXT — up to 10MB
                            </p>
                            <input
                                ref={inputRef}
                                type="file"
                                className="upload-input"
                                accept=".pdf,.docx,.txt"
                                onChange={handleInputChange}
                                id="file-upload-input"
                            />
                        </div>

                        {error && (
                            <div className="error-message" style={{ maxWidth: 600, margin: '20px auto' }}>
                                {error}
                            </div>
                        )}
                    </section>

                    <section className="features-grid">
                        {[
                            { icon: '🔍', title: 'Risk Detection', desc: 'Identifies unlimited liability, one-sided termination, and other risky patterns.' },
                            { icon: '📊', title: 'Compliance Scoring', desc: 'Checks against 12 essential legal clauses and gives you a 0–100 score.' },
                            { icon: '🌐', title: 'Bilingual Support', desc: 'Analyzes contracts in both English and Hindi with automatic language detection.' },
                            { icon: '🔒', title: 'Privacy-First', desc: 'Documents are processed in memory and deleted immediately after analysis.' },
                            { icon: '📝', title: 'Clause Breakdown', desc: 'Segments your document into individual clauses with risk labels.' },
                            { icon: '💡', title: 'Plain Explanations', desc: 'Every flagged clause comes with a simple, human-readable explanation.' },
                        ].map((f, i) => (
                            <div key={i} className={`feature-card glass-card animate-slide-up delay-${i % 5 + 1}`}>
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
