import { NavLink } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { IconScale } from './Icons';

export default function Header() {
    const [scrolled, setScrolled] = useState(false);

    useEffect(() => {
        const onScroll = () => setScrolled(window.scrollY > 20);
        window.addEventListener('scroll', onScroll, { passive: true });
        return () => window.removeEventListener('scroll', onScroll);
    }, []);

    return (
        <header className={`header ${scrolled ? 'scrolled' : ''}`}>
            <div className="header-inner">
                <NavLink to="/" className="logo">
                    <span className="logo-icon"><IconScale size={22} /></span>
                    <span>ClauseCheck</span>
                </NavLink>
                <nav className="nav-links">
                    <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} end>
                        Analyze
                    </NavLink>
                    <NavLink to="/compare" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        Compare
                    </NavLink>
                    <NavLink to="/history" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        History
                    </NavLink>
                </nav>
            </div>
        </header>
    );
}
