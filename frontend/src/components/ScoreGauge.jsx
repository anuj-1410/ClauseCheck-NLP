import { useEffect, useRef } from 'react';
import anime from 'animejs';

export default function ScoreGauge({ score, label, color }) {
    const radius = 58;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;
    const fillRef = useRef(null);

    useEffect(() => {
        if (fillRef.current) {
            anime({
                targets: fillRef.current,
                strokeDashoffset: [circumference, offset],
                duration: 1200,
                easing: 'easeOutCubic',
                delay: 200,
            });
        }
    }, [circumference, offset]);

    return (
        <div className="score-card glass-card card-3d">
            <div className="score-gauge">
                <svg viewBox="0 0 140 140">
                    <circle className="track" cx="70" cy="70" r={radius} />
                    <circle
                        ref={fillRef}
                        className="fill"
                        cx="70"
                        cy="70"
                        r={radius}
                        stroke={color}
                        strokeDasharray={circumference}
                        strokeDashoffset={circumference}
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
