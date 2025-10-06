import { MemoryRouter } from 'react-router-dom';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import App from '../App';
import { resetAuthStore, useAuthStore } from '../stores/auth';

const createJsonResponse = (data: unknown) =>
  new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });

const stubDashboardRequests = () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
    const url = input.toString();
    if (url.endsWith('/books')) {
      return Promise.resolve(createJsonResponse([]));
    }

    if (url.includes('/storage/apps/macos')) {
      return Promise.resolve(createJsonResponse({ path: 'macOS/', type: 'folder', children: [] }));
    }

    if (url.includes('/storage/apps/windows')) {
      return Promise.resolve(createJsonResponse({ path: 'windows/', type: 'folder', children: [] }));
    }

    if (url.includes('/storage/apps/linux')) {
      return Promise.resolve(createJsonResponse({ path: 'linux/', type: 'folder', children: [] }));
    }

    if (url.endsWith('/storage/trash')) {
      return Promise.resolve(createJsonResponse([]));
    }

    throw new Error(`Unexpected request to ${url}`);
  });
};

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
      isHydrated: true,
      isHydrating: false,
      error: null
    });
  });
};

beforeEach(() => {
  vi.restoreAllMocks();
  stubDashboardRequests();
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

describe('App routing', () => {
  it('renders navigation and dashboard content when authenticated', async () => {
    authenticateTestUser();
    renderApp(['/dashboard']);

    expect(screen.getByRole('navigation', { name: /primary/i })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByText(/Review stored content at a glance/i)).toBeInTheDocument();
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
