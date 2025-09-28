import { MemoryRouter } from 'react-router-dom';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import App from '../App';
import { resetAuthStore, useAuthStore } from '../stores/auth';

const renderApp = (initialEntries: string[] = ['/']) =>
  render(
    <MemoryRouter initialEntries={initialEntries}>
      <App />
    </MemoryRouter>
  );

const authenticateTestUser = () => {
  act(() => {
    useAuthStore.setState({
      token: 'test-token',
      tokenType: 'bearer',
      isAuthenticated: true,
      isAuthenticating: false,
      error: null
    });
  });
};

beforeEach(() => {
  act(() => {
    resetAuthStore();
  });
});

afterEach(() => {
  act(() => {
    resetAuthStore();
  });
});

describe('App routing', () => {
  it('renders navigation and dashboard content when authenticated', () => {
    authenticateTestUser();
    renderApp(['/dashboard']);

    expect(screen.getByRole('navigation', { name: /primary/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByText(/Welcome to the Dream Central Storage admin panel/i)).toBeInTheDocument();
  });

  it('logs out and returns to the login page', async () => {
    authenticateTestUser();
    renderApp(['/dashboard']);

    const user = userEvent.setup();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /logout/i }));
    });

    expect(await screen.findByRole('heading', { name: /admin login/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });
});
