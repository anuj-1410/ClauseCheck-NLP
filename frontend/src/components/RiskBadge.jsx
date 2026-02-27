import { IconDot } from './Icons';

export default function RiskBadge({ severity }) {
    const colors = { high: 'var(--risk-high)', medium: 'var(--risk-medium)', low: 'var(--risk-low)' };
    return (
        <span className={`risk-badge ${severity}`}>
            <IconDot size={7} color={colors[severity] || 'var(--text-muted)'} />
            {severity}
        </span>
    );
}
