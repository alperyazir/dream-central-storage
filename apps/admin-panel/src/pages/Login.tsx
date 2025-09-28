import { FormEvent, useMemo, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Container,
  Paper,
  Stack,
  TextField,
  Typography
} from '@mui/material';

import { useAuthStore } from '../stores/auth';

interface LocationState {
  from?: {
    pathname: string;
  };
}

const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const login = useAuthStore((state) => state.login);
  const error = useAuthStore((state) => state.error);
  const clearError = useAuthStore((state) => state.clearError);
  const isAuthenticating = useAuthStore((state) => state.isAuthenticating);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const isSubmitDisabled = useMemo(
    () => isAuthenticating || email.trim().length === 0 || password.length === 0,
    [email, password, isAuthenticating]
  );

  const handleEmailChange = (value: string) => {
    if (error) {
      clearError();
    }

    setEmail(value);
  };

  const handlePasswordChange = (value: string) => {
    if (error) {
      clearError();
    }

    setPassword(value);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    try {
      await login({ email, password });
      const state = location.state as LocationState | null;
      const redirectPath = state?.from?.pathname ?? '/dashboard';
      navigate(redirectPath, { replace: true });
    } catch (err) {
      // Error state handled by the auth store; no-op here to keep UX responsive.
    }
  };

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <Container maxWidth="sm" component="main">
      <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center' }}>
        <Paper elevation={3} sx={{ padding: 4, width: '100%' }}>
          <Stack spacing={3} component="form" onSubmit={handleSubmit} noValidate>
            <div>
              <Typography component="h1" variant="h4" gutterBottom>
                Admin Login
              </Typography>
              <Typography color="text.secondary">
                Enter your administrator credentials to continue.
              </Typography>
            </div>

            {error ? <Alert severity="error">{error}</Alert> : null}

            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(event) => handleEmailChange(event.target.value)}
              required
              autoComplete="username"
              fullWidth
            />

            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={(event) => handlePasswordChange(event.target.value)}
              required
              autoComplete="current-password"
              fullWidth
            />

            <Button type="submit" variant="contained" size="large" disabled={isSubmitDisabled}>
              {isAuthenticating ? 'Signing In…' : 'Sign In'}
            </Button>
          </Stack>
        </Paper>
      </Box>
    </Container>
  );
};

export default LoginPage;
