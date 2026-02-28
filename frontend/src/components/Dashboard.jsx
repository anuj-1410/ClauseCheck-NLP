import { useState, useEffect, useRef, useCallback } from 'react';
import {
    Chart as ChartJS, ArcElement, Tooltip, Legend,
    RadialLinearScale, PointElement, LineElement, Filler,
} from 'chart.js';
import { Doughnut, Radar } from 'react-chartjs-2';
import anime from 'animejs';
import { IconCheck, IconX, IconDot } from './Icons';

ChartJS.register(ArcElement, Tooltip, Legend, RadialLinearScale, PointElement, LineElement, Filler);

/* ══════════════════════════════════
   External HTML Tooltip (never clips)
   ══════════════════════════════════ */
function getOrCreateTooltipEl() {
    let el = document.getElementById('chartjs-ext-tooltip');
    if (!el) {
        el = document.createElement('div');
        el.id = 'chartjs-ext-tooltip';
        el.innerHTML = '<div class="cht-inner"></div>';
        document.body.appendChild(el);
    }
    return el;
}

function externalTooltipHandler(context) {
    const { chart, tooltip } = context;
    const tooltipEl = getOrCreateTooltipEl();

    if (tooltip.opacity === 0) {
        tooltipEl.style.opacity = '0';
        tooltipEl.style.pointerEvents = 'none';
        return;
    }

    // Build content
    const inner = tooltipEl.querySelector('.cht-inner');
    if (tooltip.body) {
        const titleLines = tooltip.title || [];
        const bodyLines = tooltip.body.map(b => b.lines);
        let html = '';
        titleLines.forEach(t => { html += `<div class="cht-title">${t}</div>`; });
        bodyLines.forEach((lines, i) => {
            const colors = tooltip.labelColors[i];
            const dot = `<span class="cht-dot" style="background:${colors.borderColor}"></span>`;
            lines.forEach(l => { html += `<div class="cht-line">${dot}${l}</div>`; });
        });
        inner.innerHTML = html;
    }

    // Position
    const { offsetLeft, offsetTop } = chart.canvas;
    const rect = chart.canvas.getBoundingClientRect();
    tooltipEl.style.opacity = '1';
    tooltipEl.style.pointerEvents = 'auto';
    tooltipEl.style.left = rect.left + window.scrollX + tooltip.caretX + 'px';
    tooltipEl.style.top = rect.top + window.scrollY + tooltip.caretY + 'px';
}

const extTooltip = {
    enabled: false,
    external: externalTooltipHandler,
};

/* ══════════════════════════════════
   Animated Counter
   ══════════════════════════════════ */
function AnimatedNumber({ value, duration = 1200, color = 'var(--text-primary)' }) {
    const ref = useRef(null);
    useEffect(() => {
        if (!ref.current) return;
        anime({
            targets: { val: 0 },
            val: value,
            duration,
            easing: 'easeOutExpo',
            round: 1,
            update(anim) {
                if (ref.current) ref.current.textContent = anim.animations[0].currentValue;
            },
        });
    }, [value, duration]);
    return <span ref={ref} style={{ color, fontFamily: 'var(--mono)', fontWeight: 800 }}>0</span>;
}

/* ══════════════════════════════════
   Score Ring (animated SVG arc)
   ══════════════════════════════════ */
function ScoreRing({ score, color, size = 110, label }) {
    const strokeWidth = 8;
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;
    const ref = useRef(null);

    useEffect(() => {
        if (!ref.current) return;
        anime({
            targets: ref.current,
            strokeDashoffset: [circumference, offset],
            duration: 1500,
            easing: 'easeOutCubic',
        });
    }, [offset, circumference]);

    return (
        <div className="score-ring-wrap" style={{ width: size, height: size }}>
            <svg width={size} height={size} className="score-ring-svg">
                <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth={strokeWidth} />
                <circle
                    ref={ref}
                    cx={size / 2} cy={size / 2} r={radius} fill="none"
                    stroke={color} strokeWidth={strokeWidth}
                    strokeDasharray={circumference} strokeDashoffset={circumference}
                    strokeLinecap="round"
                    transform={`rotate(-90 ${size / 2} ${size / 2})`}
                    style={{ filter: `drop-shadow(0 0 6px ${color}40)` }}
                />
            </svg>
            <div className="score-ring-center">
                <AnimatedNumber value={score} color={color} />
                {label && <span className="score-ring-label">{label}</span>}
            </div>
        </div>
    );
}

/* ══════════════════════════════════
   Compliance Status Grid
   ══════════════════════════════════ */
function ComplianceGrid({ details, foundCount, totalCount }) {
    const [hoveredIdx, setHoveredIdx] = useState(null);

    return (
        <div className="comp-grid-section">
            {/* Visual progress arc */}
            <div className="comp-progress-row">
                <div className="comp-arc-wrap">
                    <svg viewBox="0 0 100 55" className="comp-arc-svg">
                        {/* Background arc */}
                        <path
                            d="M 8 50 A 42 42 0 0 1 92 50"
                            fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="6" strokeLinecap="round"
                        />
                        {/* Filled arc */}
                        <path
                            d="M 8 50 A 42 42 0 0 1 92 50"
                            fill="none" stroke="url(#compGrad)" strokeWidth="6" strokeLinecap="round"
                            strokeDasharray={`${(foundCount / Math.max(totalCount, 1)) * 132} 132`}
                            className="comp-arc-fill"
                        />
                        <defs>
                            <linearGradient id="compGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" stopColor="#2dd4bf" />
                                <stop offset="100%" stopColor="#4ade80" />
                            </linearGradient>
                        </defs>
                        {/* Center text */}
                        <text x="50" y="44" textAnchor="middle" className="comp-arc-num">{foundCount}/{totalCount}</text>
                        <text x="50" y="53" textAnchor="middle" className="comp-arc-label">CLAUSES PRESENT</text>
                    </svg>
                </div>
            </div>

            {/* Interactive clause grid */}
            <div className="comp-clause-grid">
                {details.map((item, i) => {
                    const name = (item.clause_type || '').replace(/_/g, ' ');
                    return (
                        <div
                            key={i}
                            className={`comp-cell ${item.found ? 'found' : 'missing'} ${hoveredIdx === i ? 'hovered' : ''}`}
                            onMouseEnter={() => setHoveredIdx(i)}
                            onMouseLeave={() => setHoveredIdx(null)}
                        >
                            <div className="comp-cell-icon">
                                {item.found ? <IconCheck size={14} /> : <IconX size={14} />}
                            </div>
                            <span className="comp-cell-name">{name}</span>
                            {hoveredIdx === i && (
                                <div className="comp-cell-tooltip">
                                    {item.found ? 'Present in contract' : 'Missing — recommended to add'}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}


/* ══════════════════════════════════
   Main Dashboard
   ══════════════════════════════════ */
export default function Dashboard({ result, risks, compliance, responsibility }) {
    const [hoveredRisk, setHoveredRisk] = useState(null);

    // ── Risk data ──
    const highRisks = risks.filter(r => r.severity === 'high');
    const medRisks = risks.filter(r => r.severity === 'medium');
    const lowRisks = risks.filter(r => r.severity === 'low');
    const riskTypeMap = {};
    risks.forEach(r => {
        const type = (r.risk_type || 'other').replace(/_/g, ' ');
        riskTypeMap[type] = (riskTypeMap[type] || 0) + 1;
    });
    const riskTypes = Object.entries(riskTypeMap).sort((a, b) => b[1] - a[1]);

    // ── Compliance data ──
    const compDetails = compliance.details || [];
    const compFound = compDetails.filter(d => d.found).length;
    const compMissing = compDetails.filter(d => !d.found);

    // ── Ambiguity data ──
    const passiveCount = (responsibility.passive_voice || []).length;
    const vagueCount = (responsibility.vague_terms || []).length;
    const missingSubCount = (responsibility.missing_subjects || []).length;
    const totalAmbiguity = passiveCount + vagueCount + missingSubCount;

    // ── Colors ──
    const riskColor = result.risk_score > 60 ? '#f87171' : result.risk_score > 30 ? '#fbbf24' : '#4ade80';
    const compColor = result.compliance_score >= 70 ? '#4ade80' : result.compliance_score >= 40 ? '#fbbf24' : '#f87171';
    const ambColor = (responsibility.ambiguity_score || 0) > 50 ? '#fbbf24' : '#4ade80';

    // ── Verdict ──
    const verdict = result.risk_score > 60
        ? { label: 'High Risk — Review Before Signing', cls: 'verdict-danger' }
        : result.risk_score > 30
            ? { label: 'Moderate Risk — Negotiate Key Clauses', cls: 'verdict-warning' }
            : { label: 'Low Risk — Generally Safe to Proceed', cls: 'verdict-safe' };

    // ── Chart configs (external tooltip = never clips) ──
    const riskDoughnutData = {
        labels: ['High', 'Medium', 'Low'],
        datasets: [{
            data: [highRisks.length, medRisks.length, lowRisks.length],
            backgroundColor: ['rgba(248,113,113,0.7)', 'rgba(251,191,36,0.7)', 'rgba(74,222,128,0.7)'],
            borderColor: ['#f87171', '#fbbf24', '#4ade80'],
            borderWidth: 2,
            hoverBorderWidth: 3,
            hoverOffset: 8,
            spacing: 3,
        }],
    };

    const riskDoughnutOpts = {
        responsive: true,
        maintainAspectRatio: true,
        cutout: '65%',
        plugins: {
            legend: { display: false },
            tooltip: {
                ...extTooltip,
            },
        },
        animation: { animateRotate: true, animateScale: true, duration: 1200, easing: 'easeOutQuart' },
    };

    const ambRadarData = {
        labels: ['Passive Voice', 'Vague Terms', 'Missing Subjects'],
        datasets: [{
            data: [passiveCount, vagueCount, missingSubCount],
            backgroundColor: 'rgba(45,212,191,0.12)',
            borderColor: '#2dd4bf',
            borderWidth: 2,
            pointBackgroundColor: ['#f87171', '#fbbf24', '#38bdf8'],
            pointBorderColor: '#12161c',
            pointRadius: 6,
            pointHoverRadius: 10,
            pointBorderWidth: 2,
        }],
    };

    const ambRadarOpts = {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { top: 20, bottom: 20, left: 20, right: 20 } },
        plugins: {
            legend: { display: false },
            tooltip: {
                ...extTooltip,
            },
        },
        scales: {
            r: {
                ticks: { display: false, stepSize: 1 },
                grid: { color: 'rgba(45,212,191,0.06)' },
                angleLines: { color: 'rgba(45,212,191,0.08)' },
                pointLabels: {
                    color: '#8b95a5',
                    font: { size: 12, family: 'Inter', weight: '600' },
                    padding: 14,
                },
                suggestedMin: 0,
            },
        },
        animation: { duration: 1200, easing: 'easeOutQuart' },
    };

    return (
        <div className="premium-dashboard">
            {/* ═══ Verdict Banner ═══ */}
            <div className={`verdict-banner-v2 ${verdict.cls} animate-in`}>
                <div className="verdict-v2-content">
                    <span className="verdict-v2-label">{verdict.label}</span>
                    <span className="verdict-v2-detail">
                        {risks.length} risk{risks.length !== 1 ? 's' : ''} · {compFound}/{compDetails.length} clauses · {totalAmbiguity} ambiguity issue{totalAmbiguity !== 1 ? 's' : ''}
                    </span>
                </div>
                <div className="verdict-v2-scores">
                    <div className="verdict-v2-pill" style={{ borderColor: riskColor + '50' }}>
                        <span className="verdict-v2-num" style={{ color: riskColor }}>{result.risk_score}</span>
                        <span className="verdict-v2-unit">Risk</span>
                    </div>
                    <div className="verdict-v2-pill" style={{ borderColor: compColor + '50' }}>
                        <span className="verdict-v2-num" style={{ color: compColor }}>{result.compliance_score}</span>
                        <span className="verdict-v2-unit">Compliance</span>
                    </div>
                    <div className="verdict-v2-pill" style={{ borderColor: ambColor + '50' }}>
                        <span className="verdict-v2-num" style={{ color: ambColor }}>{responsibility.ambiguity_score || 0}</span>
                        <span className="verdict-v2-unit">Ambiguity</span>
                    </div>
                </div>
            </div>

            {/* ═══ Three Panels ═══ */}
            <div className="dash-panels animate-slide-up delay-1">

                {/* ─── Risk Panel ─── */}
                <div className="dash-panel glass-card">
                    <div className="dash-panel-head">
                        <ScoreRing score={result.risk_score} color={riskColor} size={90} label="Risk" />
                        <div className="dash-panel-info">
                            <h3>Risk Analysis</h3>
                            <p>{risks.length} finding{risks.length !== 1 ? 's' : ''}</p>
                        </div>
                    </div>

                    <div className="dash-chart-area">
                        <div className="dash-chart-wrap">
                            <Doughnut data={riskDoughnutData} options={riskDoughnutOpts} />
                        </div>
                        <div className="dash-chart-legend">
                            {[
                                { label: 'High', count: highRisks.length, color: '#f87171' },
                                { label: 'Medium', count: medRisks.length, color: '#fbbf24' },
                                { label: 'Low', count: lowRisks.length, color: '#4ade80' },
                            ].map(item => (
                                <div key={item.label} className="legend-row">
                                    <IconDot size={8} color={item.color} />
                                    <span className="legend-label">{item.label}</span>
                                    <span className="legend-count" style={{ color: item.color }}>{item.count}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {riskTypes.length > 0 && (
                        <div className="risk-tags">
                            {riskTypes.map(([type, count]) => (
                                <div
                                    key={type}
                                    className={`risk-tag ${hoveredRisk === type ? 'active' : ''}`}
                                    onMouseEnter={() => setHoveredRisk(type)}
                                    onMouseLeave={() => setHoveredRisk(null)}
                                >
                                    <span className="risk-tag-name">{type}</span>
                                    <span className="risk-tag-count">{count}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* ─── Compliance Panel ─── */}
                <div className="dash-panel glass-card">
                    <div className="dash-panel-head">
                        <ScoreRing score={result.compliance_score} color={compColor} size={90} label="Compliance" />
                        <div className="dash-panel-info">
                            <h3>Compliance</h3>
                            <p>{compFound}/{compDetails.length} present</p>
                        </div>
                    </div>

                    <ComplianceGrid
                        details={compDetails}
                        foundCount={compFound}
                        totalCount={compDetails.length}
                    />
                </div>

                {/* ─── Ambiguity Panel ─── */}
                <div className="dash-panel glass-card">
                    <div className="dash-panel-head">
                        <ScoreRing score={responsibility.ambiguity_score || 0} color={ambColor} size={90} label="Clarity" />
                        <div className="dash-panel-info">
                            <h3>Ambiguity & Clarity</h3>
                            <p>{totalAmbiguity} issue{totalAmbiguity !== 1 ? 's' : ''}</p>
                        </div>
                    </div>

                    {totalAmbiguity > 0 ? (
                        <>
                            <div className="dash-chart-area">
                                <div className="dash-radar-wrap">
                                    <Radar data={ambRadarData} options={ambRadarOpts} />
                                </div>
                            </div>

                            <div className="amb-breakdown">
                                {[
                                    { label: 'Passive Voice', count: passiveCount, color: '#f87171', desc: 'Unclear responsibility' },
                                    { label: 'Vague Terms', count: vagueCount, color: '#fbbf24', desc: 'Imprecise language' },
                                    { label: 'Missing Subjects', count: missingSubCount, color: '#38bdf8', desc: 'No clear actor' },
                                ].map(item => (
                                    <div key={item.label} className="amb-row">
                                        <div className="amb-indicator" style={{ background: item.color }} />
                                        <div className="amb-info">
                                            <span className="amb-label">{item.label}</span>
                                            <span className="amb-desc">{item.desc}</span>
                                        </div>
                                        <span className="amb-count" style={{ color: item.color }}>
                                            <AnimatedNumber value={item.count} color={item.color} />
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </>
                    ) : (
                        <div className="dash-empty-state">
                            <IconCheck size={32} />
                            <p>No ambiguity issues detected</p>
                            <span>This contract has clear, well-defined language</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
