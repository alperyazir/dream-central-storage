import { MemoryRouter } from 'react-router-dom';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import App from '../App';
import { resetAuthStore } from '../stores/auth';

const createJsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' }
  });

const stubDashboardRequests = () => ({
  mac: { path: 'macOS/', type: 'folder', children: [] },
  windows: { path: 'windows/', type: 'folder', children: [] }
});

const renderApp = (initialEntries: string[]) =>
  render(
    <MemoryRouter initialEntries={initialEntries}>
      <App />
    </MemoryRouter>
  );

beforeEach(() => {
  vi.restoreAllMocks();
  act(() => {
    resetAuthStore();
  });
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
    const { mac, windows } = stubDashboardRequests();
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const normalized = url.toLowerCase();

      if (url.endsWith('/auth/login')) {
        return Promise.resolve(createJsonResponse({ access_token: 'token-123', token_type: 'bearer' }));
      }

      if (url.endsWith('/books')) {
        const headers = new Headers(init?.headers as HeadersInit);
        expect(headers.get('Authorization')).toBe('Bearer token-123');
        return Promise.resolve(createJsonResponse([]));
      }

      if (normalized.includes('/storage/apps/macos')) {
        return Promise.resolve(createJsonResponse(mac));
      }

      if (normalized.includes('/storage/apps/windows')) {
        return Promise.resolve(createJsonResponse(windows));
      }

      throw new Error(`Unexpected request to ${url}`);
    });

    renderApp(['/login']);
    const user = userEvent.setup();

    await act(async () => {
      await user.type(screen.getByLabelText(/email/i), 'Admin@Example.com ');
      await user.type(screen.getByLabelText(/password/i), 'super-secret');
      await user.click(screen.getByRole('button', { name: /sign in/i }));
    });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));

    const [loginUrl, requestInit] = fetchMock.mock.calls[0];
    expect(loginUrl.toString()).toMatch(/\/auth\/login$/);
    const { body } = (requestInit ?? {}) as RequestInit;
    expect(typeof body).toBe('string');
    const parsedBody = JSON.parse(body as string);
    expect(parsedBody).toEqual({ email: 'admin@example.com', password: 'super-secret' });

    expect(await screen.findByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
  });

  it('shows an error message when authentication fails', async () => {
    const { mac, windows } = stubDashboardRequests();

    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      const normalized = url.toLowerCase();

      if (url.endsWith('/auth/login')) {
        return Promise.resolve(
          new Response('Invalid credentials', {
            status: 401,
            headers: { 'Content-Type': 'text/plain' }
          })
        );
      }

      if (url.endsWith('/books')) {
        return Promise.resolve(createJsonResponse([]));
      }

      if (normalized.includes('/storage/apps/macos')) {
        return Promise.resolve(createJsonResponse(mac));
      }

      if (normalized.includes('/storage/apps/windows')) {
        return Promise.resolve(createJsonResponse(windows));
      }

      throw new Error(`Unexpected request to ${url}`);
    });

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
