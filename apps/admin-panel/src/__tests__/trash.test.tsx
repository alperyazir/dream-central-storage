import { MemoryRouter } from 'react-router-dom';
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import App from '../App';
import { resetAuthStore, useAuthStore } from '../stores/auth';

const createJsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' }
  });

const authenticate = () => {
  act(() => {
    useAuthStore.setState({
      token: 'token',
      tokenType: 'Bearer',
      isAuthenticated: true,
      isAuthenticating: false,
      isHydrated: true,
      isHydrating: false,
      error: null
    });
  });
};

const renderTrashPage = () =>
  render(
    <MemoryRouter initialEntries={['/trash']}>
      <App />
    </MemoryRouter>
  );

describe('Trash page', () => {
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

  it('renders entries and allows restoring an item', async () => {
    authenticate();

    let restoreTriggered = false;
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const method = (init?.method ?? 'GET').toUpperCase();

      if (url.endsWith('/storage/trash') && method === 'GET') {
        if (!restoreTriggered) {
          return Promise.resolve(
            createJsonResponse([
              {
                key: 'books/Press/Atlas/',
                bucket: 'books',
                path: 'Press/Atlas',
                item_type: 'book',
                object_count: 2,
                total_size: 1024,
                metadata: { publisher: 'Press', book_name: 'Atlas' },
                youngest_last_modified: '2023-12-20T10:00:00Z',
                eligible_at: '2023-12-27T10:00:00Z',
                eligible_for_deletion: true
              }
            ])
          );
        }
        return Promise.resolve(createJsonResponse([]));
      }

      if (url.endsWith('/storage/restore') && method === 'POST') {
        restoreTriggered = true;
        return Promise.resolve(
          createJsonResponse({ restored_key: 'books/Press/Atlas/', objects_moved: 2, item_type: 'book' })
        );
      }

      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse([]));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    renderTrashPage();

    const table = await screen.findByRole('table', { name: /trash entries table/i });
    expect(within(table).getByText(/press \/ atlas/i)).toBeInTheDocument();
    expect(within(table).getByText(/eligible now/i)).toBeInTheDocument();

    const user = userEvent.setup();
    const restoreButton = within(table).getByRole('button', { name: /restore/i });

    await act(async () => {
      await user.click(restoreButton);
    });

    const confirmButton = await screen.findByRole('button', { name: /^restore$/i });

    await act(async () => {
      await user.click(confirmButton);
    });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/storage\/restore$/), expect.any(Object)));
    await waitFor(() => expect(screen.queryByRole('dialog', { name: /confirm restore/i })).not.toBeInTheDocument());
  });

  it('surfaces errors when restore fails', async () => {
    authenticate();

    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const method = (init?.method ?? 'GET').toUpperCase();

      if (url.endsWith('/storage/trash') && method === 'GET') {
        return Promise.resolve(
          createJsonResponse([
            {
              key: 'apps/macos/1.0/',
              bucket: 'apps',
              path: 'macos/1.0',
              item_type: 'app',
              object_count: 1,
              total_size: 4096,
              metadata: { platform: 'macOS', version: '1.0' },
              youngest_last_modified: '2024-03-01T08:00:00Z',
              eligible_at: '2024-03-08T08:00:00Z',
              eligible_for_deletion: false
            }
          ])
        );
      }

      if (url.endsWith('/storage/restore') && method === 'POST') {
        return Promise.resolve(new Response('failure', { status: 502 }));
      }

      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse([]));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    renderTrashPage();

    const table = await screen.findByRole('table', { name: /trash entries table/i });
    const restoreButton = within(table).getByRole('button', { name: /restore/i });
    const user = userEvent.setup();

    await act(async () => {
      await user.click(restoreButton);
    });

    const confirmButton = await screen.findByRole('button', { name: /^restore$/i });

    await act(async () => {
      await user.click(confirmButton);
    });

    expect(await screen.findByText(/unable to restore the selected item/i)).toBeInTheDocument();
  });

  it('permanently deletes an entry and shows a success message', async () => {
    authenticate();

    let deleted = false;
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const method = (init?.method ?? 'GET').toUpperCase();

      if (url.endsWith('/storage/trash') && method === 'GET') {
        if (deleted) {
          return Promise.resolve(createJsonResponse([]));
        }

        return Promise.resolve(
          createJsonResponse([
            {
              key: 'books/Press/Atlas/',
              bucket: 'books',
              path: 'Press/Atlas',
              item_type: 'book',
              object_count: 2,
              total_size: 1024,
              metadata: { publisher: 'Press', book_name: 'Atlas' },
              youngest_last_modified: '2023-12-20T10:00:00Z',
              eligible_at: '2023-12-27T10:00:00Z',
              eligible_for_deletion: true
            }
          ])
        );
      }

      if (url.endsWith('/storage/trash') && method === 'DELETE') {
        deleted = true;
        return Promise.resolve(
          createJsonResponse({ deleted_key: 'books/Press/Atlas/', objects_removed: 2, item_type: 'book' })
        );
      }

      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse([]));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    renderTrashPage();

    const table = await screen.findByRole('table', { name: /trash entries table/i });
    const deleteButton = within(table).getByRole('button', { name: /^delete$/i });
    const user = userEvent.setup();

    await act(async () => {
      await user.click(deleteButton);
    });

    const confirmButton = await screen.findByRole('button', { name: /^delete$/i });
    await act(async () => {
      await user.click(confirmButton);
    });

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringMatching(/storage\/trash$/),
        expect.objectContaining({
          method: 'DELETE',
          body: JSON.stringify({ key: 'books/Press/Atlas/', force: false })
        })
      )
    );

    expect(await screen.findByText(/permanently deleted/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('dialog', { name: /delete permanently/i })).not.toBeInTheDocument());
  });

  it('disables delete until the retention window expires', async () => {
    authenticate();
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-01-01T00:00:00Z'));

    try {
      vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();
        const method = (init?.method ?? 'GET').toUpperCase();

        if (url.endsWith('/storage/trash') && method === 'GET') {
          return Promise.resolve(
            createJsonResponse([
              {
                key: 'apps/windows/3.0/',
                bucket: 'apps',
                path: 'windows/3.0',
                item_type: 'app',
                object_count: 4,
                total_size: 8192,
                metadata: { platform: 'Windows', version: '3.0' },
                youngest_last_modified: '2024-12-31T23:58:00Z',
                eligible_at: '2025-01-01T00:02:00Z',
                eligible_for_deletion: false
              }
            ])
          );
        }

      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse([]));
      }
        throw new Error(`Unexpected request to ${url}`);
      });

      renderTrashPage();

      const table = await screen.findByRole('table', { name: /trash entries table/i });
      const deleteButton = within(table).getByRole('button', { name: /^delete$/i });
      expect(deleteButton).toBeDisabled();
      expect(within(table).getByText(/eligible in 2 minutes/i)).toBeInTheDocument();
      expect(within(table).getByRole('button', { name: /override/i })).toBeEnabled();

      await act(async () => {
        vi.advanceTimersByTime(2 * 60 * 1000);
      });

      await waitFor(() => expect(deleteButton).not.toBeDisabled());
      expect(within(table).getByText(/eligible now/i)).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it('shows retention errors when permanent deletion is blocked', async () => {
    authenticate();

    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const method = (init?.method ?? 'GET').toUpperCase();

      if (url.endsWith('/storage/trash') && method === 'GET') {
        return Promise.resolve(
          createJsonResponse([
            {
              key: 'apps/macos/2.0/',
              bucket: 'apps',
              path: 'macos/2.0',
              item_type: 'app',
              object_count: 3,
              total_size: 4096,
              metadata: { platform: 'macOS', version: '2.0' },
              youngest_last_modified: '2024-03-01T08:00:00Z',
              eligible_at: '2024-03-08T08:00:00Z',
              eligible_for_deletion: true
            }
          ])
        );
      }

      if (url.endsWith('/storage/trash') && method === 'DELETE') {
        return Promise.resolve(
          new Response(JSON.stringify({ detail: 'Trash entry is still within the mandatory retention window' }), {
            status: 409,
            headers: { 'Content-Type': 'application/json' }
          })
        );
      }

      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse([]));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    renderTrashPage();

    const table = await screen.findByRole('table', { name: /trash entries table/i });
    const deleteButton = within(table).getByRole('button', { name: /^delete$/i });
    const user = userEvent.setup();

    await act(async () => {
      await user.click(deleteButton);
    });

    const confirmButton = await screen.findByRole('button', { name: /^delete$/i });
    await act(async () => {
      await user.click(confirmButton);
    });

    expect(await screen.findByText(/mandatory retention window/i)).toBeInTheDocument();
    expect(screen.getByRole('dialog', { name: /delete permanently/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /override retention/i })).toBeInTheDocument();
  });

  it('allows overriding the retention window with justification', async () => {
    authenticate();

    let deleted = false;
    let trashRequests = 0;

    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const method = (init?.method ?? 'GET').toUpperCase();

      if (url.endsWith('/storage/trash') && method === 'GET') {
        trashRequests += 1;
        if (deleted || trashRequests > 1) {
          return Promise.resolve(createJsonResponse([]));
        }

        return Promise.resolve(
          createJsonResponse([
            {
              key: 'apps/linux/1.4.6/',
              bucket: 'apps',
              path: 'linux/1.4.6',
              item_type: 'app',
              object_count: 3,
              total_size: 4096,
              metadata: { platform: 'Linux', version: '1.4.6' },
              youngest_last_modified: '2024-04-01T08:00:00Z',
              eligible_at: '2024-04-08T08:00:00Z',
              eligible_for_deletion: true
            }
          ])
        );
      }

      if (url.endsWith('/storage/trash') && method === 'DELETE') {
        const body = JSON.parse((init?.body as string) ?? '{}');
        if (!body.force) {
          return Promise.resolve(
            new Response(
              JSON.stringify({ detail: 'Trash entry is still within the mandatory retention window' }),
              {
                status: 409,
                headers: { 'Content-Type': 'application/json' }
              }
            )
          );
        }

        expect(body.override_reason).toBe('Compliance approval 42');
        deleted = true;
        return Promise.resolve(
          createJsonResponse({ deleted_key: 'apps/linux/1.4.6/', objects_removed: 5, item_type: 'app' })
        );
      }

      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse([]));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    renderTrashPage();

    const table = await screen.findByRole('table', { name: /trash entries table/i });
    const deleteButton = within(table).getByRole('button', { name: /^delete$/i });
    const user = userEvent.setup();

    await act(async () => {
      await user.click(deleteButton);
    });

    const confirmDelete = await screen.findByRole('button', { name: /^delete$/i });
    await act(async () => {
      await user.click(confirmDelete);
    });

    const overrideButton = await screen.findByRole('button', { name: /override retention/i });

    await act(async () => {
      await user.click(overrideButton);
    });

    const justificationField = await screen.findByLabelText(/override justification/i);
    await act(async () => {
      await user.clear(justificationField);
      await user.type(justificationField, 'Compliance approval 42');
    });

    const overrideSubmit = await screen.findByRole('button', { name: /override deletion/i });
    await act(async () => {
      await user.click(overrideSubmit);
    });

    expect(await screen.findByText(/override deletion completed/i)).toBeInTheDocument();
    await waitFor(() =>
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringMatching(/storage\/trash$/),
        expect.objectContaining({
          method: 'DELETE',
          body: JSON.stringify({
            key: 'apps/linux/1.4.6/',
            force: true,
            override_reason: 'Compliance approval 42'
          })
        })
      )
    );
  });
});
