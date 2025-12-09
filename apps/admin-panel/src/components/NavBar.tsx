import { useCallback } from 'react';
import { NavLink } from 'react-router-dom';
import { IconButton, Tooltip } from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import AppsIcon from '@mui/icons-material/Apps';
import DeleteIcon from '@mui/icons-material/Delete';
import LogoutIcon from '@mui/icons-material/Logout';
import LoginIcon from '@mui/icons-material/Login';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';

import { useAuthStore } from '../stores/auth';
import { useThemeStore } from '../stores/theme';

import '../styles/navbar.css';

const NavBar = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const logout = useAuthStore((state) => state.logout);
  const mode = useThemeStore((state) => state.mode);
  const toggleMode = useThemeStore((state) => state.toggleMode);

  const handleLogout = useCallback(() => {
    logout();
  }, [logout]);

  return (
    <nav className="nav" aria-label="Primary navigation">
      <div className="nav__brand">
        <span>Dream Central Storage</span>
        <Tooltip title={mode === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}>
          <IconButton onClick={toggleMode} color="inherit" size="small" sx={{ ml: 1 }}>
            {mode === 'light' ? <Brightness4Icon fontSize="small" /> : <Brightness7Icon fontSize="small" />}
          </IconButton>
        </Tooltip>
      </div>
      <ul className="nav__links">
        <li>
          <NavLink to="/dashboard" end className={({ isActive }) => (isActive ? 'active' : '')}>
            <DashboardIcon fontSize="small" />
            <span>Dashboard</span>
          </NavLink>
        </li>
        <li>
          <NavLink to="/books" className={({ isActive }) => (isActive ? 'active' : '')}>
            <MenuBookIcon fontSize="small" />
            <span>Books</span>
          </NavLink>
        </li>
        <li>
          <NavLink to="/apps" className={({ isActive }) => (isActive ? 'active' : '')}>
            <AppsIcon fontSize="small" />
            <span>Applications</span>
          </NavLink>
        </li>
        <li>
          <NavLink to="/trash" className={({ isActive }) => (isActive ? 'active' : '')}>
            <DeleteIcon fontSize="small" />
            <span>Trash</span>
          </NavLink>
        </li>
        {isAuthenticated ? (
          <li>
            <button type="button" className="nav__button" onClick={handleLogout}>
              <LogoutIcon fontSize="small" />
              <span>Logout</span>
            </button>
          </li>
        ) : (
          <li>
            <NavLink to="/login" className={({ isActive }) => (isActive ? 'active' : '')}>
              <LoginIcon fontSize="small" />
              <span>Login</span>
            </NavLink>
          </li>
        )}
      </ul>
    </nav>
  );
};

export default NavBar;
