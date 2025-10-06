import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';

import MainLayout from './layouts/MainLayout';
import DashboardPage from './pages/Dashboard';
import LoginPage from './pages/Login';
import TrashPage from './pages/Trash';
import ProtectedRoute from './routes/ProtectedRoute';
import { useAuthStore } from './stores/auth';

const App = () => {
  const hydrate = useAuthStore((state) => state.hydrate);
  const isHydrated = useAuthStore((state) => state.isHydrated);
  const isHydrating = useAuthStore((state) => state.isHydrating);

  useEffect(() => {
    hydrate().catch((error) => {
      console.error('Failed to hydrate auth session', error);
    });
  }, [hydrate]);

  if (!isHydrated || isHydrating) {
    return (
      <Box
        component="section"
        sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 2 }}
      >
        <CircularProgress aria-label="Preparing session" />
        <Typography variant="body1" color="text.secondary">
          Preparing your session…
        </Typography>
      </Box>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="trash" element={<TrashPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};

export default App;
