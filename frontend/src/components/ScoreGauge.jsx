export default function ScoreGauge({ score, label, color }) {
    const radius = 58;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;

    return (
        <div className="score-card glass-card animate-slide-up">
            <div className="score-gauge">
                <svg viewBox="0 0 140 140">
                    <circle className="track" cx="70" cy="70" r={radius} />
                    <circle
                        className="fill"
                        cx="70"
                        cy="70"
                        r={radius}
                        stroke={color}
                        strokeDasharray={circumference}
                        strokeDashoffset={offset}
                    />
                </svg>
                <div className="score-value" style={{ color }}>
                    {score}
                </div>
            </div>
            <div className="score-label">{label}</div>
        </div>
    );
}
