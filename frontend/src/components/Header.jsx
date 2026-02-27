import { NavLink } from 'react-router-dom';

export default function Header() {
    return (
        <header className="header">
            <div className="header-inner">
                <NavLink to="/" className="logo">
                    <span className="logo-icon">⚖️</span>
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
