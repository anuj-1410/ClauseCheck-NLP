import { useEffect, useRef, useState } from 'react';
import anime from 'animejs';

/**
 * Custom hook for scroll-triggered reveal animations using IntersectionObserver + anime.js
 * @param {Object} options
 * @param {number} options.threshold - Intersection threshold (0–1), default 0.15
 * @param {number} options.staggerDelay - Delay between child elements (ms), default 60
 * @param {boolean} options.staggerChildren - Whether to stagger animate children, default false
 * @param {string} options.animation - Animation type: 'slideUp' | 'fadeIn' | 'tiltIn', default 'slideUp'
 */
export default function useScrollReveal({
    threshold = 0.15,
    staggerDelay = 60,
    staggerChildren = false,
    animation = 'slideUp',
} = {}) {
    const ref = useRef(null);
    const [isVisible, setIsVisible] = useState(false);
    const hasAnimated = useRef(false);

    useEffect(() => {
        const el = ref.current;
        if (!el) return;

        // Respect reduced motion
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (prefersReducedMotion) {
            setIsVisible(true);
            el.style.opacity = '1';
            return;
        }

        // Set initial hidden state
        if (staggerChildren) {
            // Hide individual children, keep parent visible for IntersectionObserver
            Array.from(el.children).forEach(child => {
                child.style.opacity = '0';
            });
        } else {
            el.style.opacity = '0';
        }

        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting && !hasAnimated.current) {
                    hasAnimated.current = true;
                    setIsVisible(true);

                    const targets = staggerChildren
                        ? el.children
                        : el;

                    const baseProps = {
                        targets,
                        opacity: [0, 1],
                        easing: 'easeOutCubic',
                        duration: 700,
                    };

                    if (staggerChildren) {
                        baseProps.delay = anime.stagger(staggerDelay);
                    }

                    switch (animation) {
                        case 'slideUp':
                            anime({
                                ...baseProps,
                                translateY: [30, 0],
                            });
                            break;
                        case 'fadeIn':
                            anime(baseProps);
                            break;
                        case 'tiltIn':
                            anime({
                                ...baseProps,
                                translateY: [20, 0],
                                rotateX: [8, 0],
                                duration: 800,
                            });
                            break;
                        default:
                            anime({
                                ...baseProps,
                                translateY: [30, 0],
                            });
                    }

                    observer.disconnect();
                }
            },
            { threshold }
        );

        observer.observe(el);

        return () => observer.disconnect();
    }, [threshold, staggerDelay, staggerChildren, animation]);

    return { ref, isVisible };
}
