import { NavLink } from 'react-router-dom';

import '../styles/navbar.css';

const NavBar = () => {
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
          <NavLink to="/login" className={({ isActive }) => (isActive ? 'active' : '')}>
            Login
          </NavLink>
        </li>
      </ul>
    </nav>
  );
};

export default NavBar;
