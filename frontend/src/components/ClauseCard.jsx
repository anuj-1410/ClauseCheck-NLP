import { useState } from 'react';
import RiskBadge from './RiskBadge';

export default function ClauseCard({ clause, risks, explanations }) {
    const [expanded, setExpanded] = useState(false);

    // Find risks for this clause
    const clauseRisks = risks.filter(r => r.clause_id === clause.id);
    const clauseExplanations = explanations.filter(e => e.clause_id === clause.id);

    const highestSeverity = clauseRisks.length > 0
        ? clauseRisks.reduce((max, r) => {
            const order = { high: 3, medium: 2, low: 1 };
            return (order[r.severity] || 0) > (order[max] || 0) ? r.severity : max;
        }, 'low')
        : null;

    return (
        <div className="clause-card glass-card" onClick={() => setExpanded(!expanded)}>
            <div className="clause-card-header">
                <span className="clause-id">
                    {clause.section_number ? `§${clause.section_number}` : `#${clause.id}`}
                </span>
                <p className="clause-text">
                    {expanded ? clause.text : clause.text.slice(0, 200) + (clause.text.length > 200 ? '...' : '')}
                </p>
                {highestSeverity && <RiskBadge severity={highestSeverity} />}
            </div>

            {expanded && clauseExplanations.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                    {clauseExplanations.map((exp, i) => (
                        <div key={i} className="explanation-panel">
                            <strong style={{ color: 'var(--accent-purple)' }}>{exp.risk_type?.replace(/_/g, ' ')}</strong>
                            <p style={{ marginTop: '6px' }}>{exp.explanation}</p>
                            {exp.flagged_text && (
                                <p style={{ marginTop: '8px', fontStyle: 'italic', color: 'var(--text-muted)' }}>
                                    Matched: "{exp.flagged_text}"
                                </p>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {expanded && clauseRisks.length === 0 && (
                <div className="explanation-panel" style={{ borderLeftColor: 'var(--risk-low)' }}>
                    ✅ No risks detected in this clause.
                </div>
            )}
        </div>
    );
}
