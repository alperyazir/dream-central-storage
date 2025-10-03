import { useCallback } from 'react';
import { NavLink } from 'react-router-dom';

import { useAuthStore } from '../stores/auth';

import '../styles/navbar.css';

const NavBar = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = useCallback(() => {
    logout();
  }, [logout]);

  return (
    <nav className="nav" aria-label="Primary navigation">
      <div className="nav__brand">Dream Central Storage</div>
      <ul className="nav__links">
        <li>
          <NavLink to="/dashboard" end className={({ isActive }) => (isActive ? 'active' : '')}>
            Dashboard
          </NavLink>
        </li>
        <li>
          <NavLink to="/trash" className={({ isActive }) => (isActive ? 'active' : '')}>
            Trash
          </NavLink>
        </li>
        {isAuthenticated ? (
          <li>
            <button type="button" className="nav__button" onClick={handleLogout}>
              Logout
            </button>
          </li>
        ) : (
          <li>
            <NavLink to="/login" className={({ isActive }) => (isActive ? 'active' : '')}>
              Login
            </NavLink>
          </li>
        )}
      </ul>
    </nav>
  );
};

export default NavBar;
