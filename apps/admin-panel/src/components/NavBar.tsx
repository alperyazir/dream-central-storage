import { useCallback } from 'react';
import { NavLink } from 'react-router-dom';
import { IconButton, Tooltip, List } from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import BusinessIcon from '@mui/icons-material/Business';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import AppsIcon from '@mui/icons-material/Apps';
import SchoolIcon from '@mui/icons-material/School';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import SettingsIcon from '@mui/icons-material/Settings';
import VisibilityIcon from '@mui/icons-material/Visibility';
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
      <List component="ul" className="nav__links" sx={{ p: 0, m: 0 }}>
        <li>
          <NavLink to="/dashboard" end className={({ isActive }) => (isActive ? 'active' : '')}>
            <DashboardIcon fontSize="small" />
            <span>Dashboard</span>
          </NavLink>
        </li>
        <li>
          <NavLink to="/publishers" className={({ isActive }) => (isActive ? 'active' : '')}>
            <BusinessIcon fontSize="small" />
            <span>Publishers</span>
          </NavLink>
        </li>
        <li>
          <NavLink to="/books" className={({ isActive }) => (isActive ? 'active' : '')}>
            <MenuBookIcon fontSize="small" />
            <span>All Books</span>
          </NavLink>
        </li>
        <li>
          <NavLink to="/processing" className={({ isActive }) => (isActive ? 'active' : '')}>
            <SmartToyIcon fontSize="small" />
            <span>AI Processing</span>
          </NavLink>
        </li>
        <li>
          <NavLink to="/processing/settings" className={({ isActive }) => (isActive ? 'active' : '')}>
            <SettingsIcon fontSize="small" />
            <span>AI Settings</span>
          </NavLink>
        </li>
        <li>
          <NavLink to="/ai-data" className={({ isActive }) => (isActive ? 'active' : '')}>
            <VisibilityIcon fontSize="small" />
            <span>AI Data Viewer</span>
          </NavLink>
        </li>
        <li>
          <NavLink to="/apps" className={({ isActive }) => (isActive ? 'active' : '')}>
            <AppsIcon fontSize="small" />
            <span>Applications</span>
          </NavLink>
        </li>
        <li>
          <NavLink to="/teachers" className={({ isActive }) => (isActive ? 'active' : '')}>
            <SchoolIcon fontSize="small" />
            <span>Teachers</span>
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
      </List>
    </nav>
  );
};

export default NavBar;
