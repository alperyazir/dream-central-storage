import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';

import MainLayout from './layouts/MainLayout';
import DashboardPage from './pages/Dashboard';
import PublishersPage from './pages/Publishers';
import PublisherDetailPage from './pages/PublisherDetail';
import BooksPage from './pages/Books';
import AppsPage from './pages/Apps';
import BundlesPage from './pages/Bundles';
import TeachersPage from './pages/TeachersManagement';
import LoginPage from './pages/Login';
import TrashPage from './pages/Trash';
import ProcessingPage from './pages/Processing';
import ProcessingSettingsPage from './pages/ProcessingSettings';
import AIDataViewerPage from './pages/AIDataViewer';
import TeacherDetailPage from './pages/TeacherDetail';
import ProtectedRoute from './routes/ProtectedRoute';
import { useAuthStore } from './stores/auth';
import { useThemeStore } from './stores/theme';

const App = () => {
  const hydrate = useAuthStore((state) => state.hydrate);
  const isHydrated = useAuthStore((state) => state.isHydrated);
  const isHydrating = useAuthStore((state) => state.isHydrating);
  const themeMode = useThemeStore((state) => state.mode);

  useEffect(() => {
    hydrate().catch((error) => {
      console.error('Failed to hydrate auth session', error);
    });
  }, [hydrate]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', themeMode);
  }, [themeMode]);

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
          <Route path="publishers" element={<PublishersPage />} />
          <Route path="publishers/:id" element={<PublisherDetailPage />} />
          <Route path="books" element={<BooksPage />} />
          <Route path="apps" element={<AppsPage />} />
          <Route path="bundles" element={<BundlesPage />} />
          <Route path="teachers" element={<TeachersPage />} />
          <Route path="teachers/:id" element={<TeacherDetailPage />} />
          <Route path="processing" element={<ProcessingPage />} />
          <Route path="processing/settings" element={<ProcessingSettingsPage />} />
          <Route path="ai-data" element={<AIDataViewerPage />} />
          <Route path="trash" element={<TrashPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};

export default App;
