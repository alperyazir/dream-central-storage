import { MemoryRouter } from 'react-router-dom';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import App from '../App';
import { resetAuthStore } from '../stores/auth';

const renderApp = (initialEntries: string[]) =>
  render(
    <MemoryRouter initialEntries={initialEntries}>
      <App />
    </MemoryRouter>
  );

beforeEach(() => {
  act(() => {
    resetAuthStore();
  });
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
  act(() => {
    resetAuthStore();
  });
});

describe('Authentication flows', () => {
  it('redirects unauthenticated users to the login page for protected routes', async () => {
    renderApp(['/dashboard']);

    expect(await screen.findByRole('heading', { name: /admin login/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  });

  it('successfully signs in and navigates to the dashboard', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ access_token: 'token-123', token_type: 'bearer' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      })
    );

    renderApp(['/login']);
    const user = userEvent.setup();

    await act(async () => {
      await user.type(screen.getByLabelText(/email/i), 'Admin@Example.com ');
      await user.type(screen.getByLabelText(/password/i), 'super-secret');
      await user.click(screen.getByRole('button', { name: /sign in/i }));
    });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    const [, requestInit] = fetchMock.mock.calls[0];
    const { body } = (requestInit ?? {}) as RequestInit;
    expect(typeof body).toBe('string');
    const parsedBody = JSON.parse(body as string);
    expect(parsedBody).toEqual({ email: 'admin@example.com', password: 'super-secret' });

    expect(await screen.findByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
  });

  it('shows an error message when authentication fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response('Invalid credentials', {
        status: 401,
        headers: { 'Content-Type': 'text/plain' }
      })
    );

    renderApp(['/login']);
    const user = userEvent.setup();

    await act(async () => {
      await user.type(screen.getByLabelText(/email/i), 'admin@example.com');
      await user.type(screen.getByLabelText(/password/i), 'wrong-password');
      await user.click(screen.getByRole('button', { name: /sign in/i }));
    });

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid email or password/i);
    expect(screen.getByRole('button', { name: /sign in/i })).not.toBeDisabled();
  });
});
