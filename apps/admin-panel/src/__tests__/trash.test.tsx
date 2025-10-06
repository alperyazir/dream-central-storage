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
                metadata: { publisher: 'Press', book_name: 'Atlas' }
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

      throw new Error(`Unexpected request to ${url}`);
    });

    renderTrashPage();

    const table = await screen.findByRole('table', { name: /trash entries table/i });
    expect(within(table).getByText(/press \/ atlas/i)).toBeInTheDocument();

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
              metadata: { platform: 'macOS', version: '1.0' }
            }
          ])
        );
      }

      if (url.endsWith('/storage/restore') && method === 'POST') {
        return Promise.resolve(new Response('failure', { status: 502 }));
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
              metadata: { publisher: 'Press', book_name: 'Atlas' }
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
        expect.objectContaining({ method: 'DELETE' })
      )
    );

    expect(await screen.findByText(/permanently deleted/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('dialog', { name: /delete permanently/i })).not.toBeInTheDocument());
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
              metadata: { platform: 'macOS', version: '2.0' }
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
  });
});
