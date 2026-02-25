export default function RiskBadge({ severity }) {
    const icons = { high: '🔴', medium: '🟡', low: '🟢' };
    return (
        <span className={`risk-badge ${severity}`}>
            {icons[severity] || '⚪'} {severity}
        </span>
    );
}
