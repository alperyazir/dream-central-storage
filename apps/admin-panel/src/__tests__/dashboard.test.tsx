import { MemoryRouter } from 'react-router-dom';
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import App from '../App';
import { resetAuthStore, useAuthStore } from '../stores/auth';

const authenticateTestUser = () => {
  act(() => {
    useAuthStore.setState({
      token: 'test-token',
      tokenType: 'Bearer',
      isAuthenticated: true,
      isAuthenticating: false,
      error: null
    });
  });
};

const renderDashboard = () =>
  render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <App />
    </MemoryRouter>
  );

const createJsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' }
  });

describe('Dashboard', () => {
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

  it('redirects unauthenticated users without issuing data requests', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch');

    renderDashboard();

    expect(await screen.findByRole('heading', { name: /admin login/i })).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('loads and displays book and application build data', async () => {
    authenticateTestUser();

    const booksPayload = [
      {
        id: 1,
        publisher: 'Dream Press',
        book_name: 'Dream Atlas',
        language: 'English',
        category: 'Fiction',
        status: 'published'
      },
      {
        id: 2,
        publisher: 'Nebula House',
        book_name: 'Star Charts',
        language: 'Spanish',
        category: 'Reference',
        status: 'published'
      }
    ];

    const macAppTree = {
      path: 'macOS/',
      type: 'folder',
      children: [
        {
          path: 'macOS/1.0.0/',
          type: 'folder',
          children: [
            {
              path: 'macOS/1.0.0/app.zip',
              type: 'file',
              size: 1_048_576
            },
            {
              path: 'macOS/1.0.0/Readme.md',
              type: 'file',
              size: 512
            }
          ]
        }
      ]
    };

    const windowsAppTree = {
      path: 'windows/',
      type: 'folder',
      children: [
        {
          path: 'windows/2.5.1/',
          type: 'folder',
          children: [
            {
              path: 'windows/2.5.1/installer.exe',
              type: 'file',
              size: 2_097_152
            }
          ]
        }
      ]
    };

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const normalized = url.toLowerCase();

      if (url.endsWith('/books')) {
        const headers = new Headers(init?.headers as HeadersInit);
        expect(headers.get('Authorization')).toBe('Bearer test-token');
        return Promise.resolve(createJsonResponse(booksPayload));
      }
      if (normalized.includes('/storage/apps/macos')) {
        const headers = new Headers(init?.headers as HeadersInit);
        expect(headers.get('Authorization')).toBe('Bearer test-token');
        return Promise.resolve(createJsonResponse(macAppTree));
      }
      if (normalized.includes('/storage/apps/windows')) {
        return Promise.resolve(createJsonResponse(windowsAppTree));
      }

      throw new Error(`Unexpected request to ${url}`);
    });

    renderDashboard();

    const booksTable = await screen.findByRole('table', { name: /books table/i });
    expect(await within(booksTable).findByText(/dream atlas/i)).toBeInTheDocument();
    expect(within(booksTable).getByText(/star charts/i)).toBeInTheDocument();

    const buildsTable = await screen.findByRole('table', { name: /application builds table/i });
    const buildRows = within(buildsTable).getAllByRole('row').slice(1);
    expect(buildRows).toHaveLength(2);
    expect(buildRows[0]).toHaveTextContent(/macos/i);
    expect(buildRows[0]).toHaveTextContent(/1\.0\.0/i);
    expect(buildRows[0]).toHaveTextContent(/2 files/i);
    expect(buildRows[1]).toHaveTextContent(/windows/i);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
  });

  it('filters books by publisher and toggles sorting', async () => {
    authenticateTestUser();

    const booksPayload = [
      {
        id: 1,
        publisher: 'Dream Press',
        book_name: 'Beta Manual',
        language: 'English',
        category: 'Fiction',
        status: 'published'
      },
      {
        id: 2,
        publisher: 'Nebula House',
        book_name: 'Alpha Guide',
        language: 'French',
        category: 'Reference',
        status: 'draft'
      }
    ];

    const emptyTree = { path: 'macOS/', type: 'folder', children: [] };

    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith('/books')) {
        return Promise.resolve(createJsonResponse(booksPayload));
      }
      return Promise.resolve(createJsonResponse(emptyTree));
    });

    renderDashboard();

    const booksTable = await screen.findByRole('table', { name: /books table/i });

    await within(booksTable).findByText(/alpha guide/i);
    const initialRows = within(booksTable).getAllByRole('row').slice(1);
    expect(initialRows[0]).toHaveTextContent(/alpha guide/i);
    expect(initialRows[1]).toHaveTextContent(/beta manual/i);

    const user = userEvent.setup();
    const publisherSelect = screen.getByLabelText(/publisher/i);

    await act(async () => {
      await user.click(publisherSelect);
    });
    const dreamPressOption = await screen.findByRole('option', { name: /dream press/i });
    await act(async () => {
      await user.click(dreamPressOption);
    });

    expect(within(booksTable).getAllByRole('row')).toHaveLength(2);
    expect(within(booksTable).getByText(/beta manual/i)).toBeInTheDocument();

    const titleHeader = within(booksTable).getByRole('button', { name: /title/i });
    await act(async () => {
      await user.click(titleHeader);
    });

    const sortedRows = within(booksTable).getAllByRole('row').slice(1);
    expect(sortedRows[0]).toHaveTextContent(/beta manual/i);
  });

  it('surfaces errors when data fetching fails', async () => {
    authenticateTestUser();

    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith('/books')) {
        return Promise.reject(new Error('boom'));
      }
      return Promise.resolve(createJsonResponse({ path: 'macOS/', type: 'folder', children: [] }));
    });

    renderDashboard();

    expect(await screen.findByRole('alert')).toHaveTextContent(/boom/i);
  });

  it('opens the upload dialog and shows contextual instructions', async () => {
    authenticateTestUser();

    const booksPayload = [
      {
        id: 1,
        publisher: 'Dream Press',
        book_name: 'Dream Atlas',
        language: 'English',
        category: 'Fiction',
        status: 'published'
      }
    ];

    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      if (url.endsWith('/books')) {
        const headers = new Headers(init?.headers as HeadersInit);
        expect(headers.get('Authorization')).toBe('Bearer test-token');
        return Promise.resolve(createJsonResponse(booksPayload));
      }

      if (url.includes('/storage/apps/')) {
        return Promise.resolve(createJsonResponse({ path: 'macOS/', type: 'folder', children: [] }));
      }

      throw new Error(`Unexpected request to ${url}`);
    });

    renderDashboard();

    await screen.findByRole('table', { name: /books table/i });

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /upload/i }));
    });

    const dialog = screen.getByRole('dialog', { name: /upload content/i });
    expect(dialog).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /^book$/i })).toHaveAttribute('aria-selected', 'true');
    expect(within(dialog).getByRole('tab', { name: /new book/i })).toHaveAttribute('aria-selected', 'true');
    expect(within(dialog).getByText(/includes config\.json/i)).toBeInTheDocument();

    await act(async () => {
      await user.click(within(dialog).getByRole('tab', { name: /update existing/i }));
    });

    expect(within(dialog).getByRole('tab', { name: /update existing/i })).toHaveAttribute('aria-selected', 'true');
    expect(within(dialog).getByText(/select the catalog entry to update/i)).toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByRole('tab', { name: /application/i }));
    });

    expect(within(dialog).getByText(/zipped application build/i)).toBeInTheDocument();
    expect(within(dialog).getByText(/platform\/version/i)).toBeInTheDocument();
  });

  it('uploads a book archive and refreshes dashboard data', async () => {
    authenticateTestUser();

    const booksPayload = [
      {
        id: 1,
        publisher: 'Dream Press',
        book_name: 'Dream Atlas',
        language: 'English',
        category: 'Fiction',
        status: 'published'
      }
    ];

    const buildTree = { path: 'macOS/', type: 'folder', children: [] };

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const method = (init?.method ?? 'GET').toUpperCase();

      if (url.endsWith('/books') && method === 'GET') {
        const headers = new Headers(init?.headers as HeadersInit);
        expect(headers.get('Authorization')).toBe('Bearer test-token');
        return Promise.resolve(createJsonResponse(booksPayload));
      }

      if (url.includes('/storage/apps/') && method === 'GET') {
        return Promise.resolve(createJsonResponse(buildTree));
      }

      if (url.endsWith('/books/1/upload') && method === 'POST') {
        const headers = new Headers(init?.headers as HeadersInit);
        expect(headers.get('Authorization')).toBe('Bearer test-token');
        expect(init?.body).toBeInstanceOf(FormData);
        const formData = init?.body as FormData;
        const file = formData.get('file');
        expect(file).toBeInstanceOf(File);
        expect((file as File).name).toBe('book.zip');
        return Promise.resolve(createJsonResponse({ book_id: 1, files: [{ path: 'dream/file.json', size: 128 }] }));
      }

      throw new Error(`Unexpected request to ${url}`);
    });

    renderDashboard();

    await screen.findByRole('table', { name: /books table/i });

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /upload/i }));
    });

    const dialog = screen.getByRole('dialog', { name: /upload content/i });
    const fileInput = within(dialog).getByTestId('upload-archive-input');

    await act(async () => {
      await user.click(within(dialog).getByRole('tab', { name: /update existing/i }));
    });

    await act(async () => {
      await user.click(within(dialog).getByLabelText(/target book/i));
    });
    const bookOption = await screen.findByRole('option', { name: /dream atlas/i });
    await act(async () => {
      await user.click(bookOption);
    });

    await act(async () => {
      const archive = new File(['dummy'], 'book.zip', { type: 'application/zip' });
      await user.upload(fileInput, archive);
    });

    await act(async () => {
      await user.click(within(dialog).getByRole('button', { name: /^upload$/i }));
    });

    await within(dialog).findByText(/uploaded 1 file/i);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(7));
  });

  it('uploads a new book archive without requiring a target selection', async () => {
    authenticateTestUser();

    const booksPayload: unknown[] = [];

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const method = (init?.method ?? 'GET').toUpperCase();

      if (url.endsWith('/books') && method === 'GET') {
        return Promise.resolve(createJsonResponse(booksPayload));
      }

      if (url.includes('/storage/apps/') && method === 'GET') {
        return Promise.resolve(createJsonResponse({ path: 'macOS/', type: 'folder', children: [] }));
      }

      if (url.endsWith('/books/upload') && method === 'POST') {
        const formData = init?.body as FormData;
        expect(formData.get('file')).toBeInstanceOf(File);
        return Promise.resolve(
          createJsonResponse({
            book: {
              id: 42,
              publisher: 'Aurora Press',
              book_name: 'Aurora Atlas',
              language: 'English',
              category: 'Fiction',
              status: 'published'
            },
            files: [{ path: 'Aurora Press/Aurora Atlas/chapter1.txt', size: 256 }]
          })
        );
      }

      throw new Error(`Unexpected request to ${url}`);
    });

    renderDashboard();

    await screen.findByRole('table', { name: /books table/i });

    const user = userEvent.setup();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /upload/i }));
    });

    const dialog = screen.getByRole('dialog', { name: /upload content/i });
    const fileInput = within(dialog).getByTestId('upload-archive-input');

    await act(async () => {
      const archive = new File(['dummy'], 'book.zip', { type: 'application/zip' });
      await user.upload(fileInput, archive);
    });

    await act(async () => {
      await user.click(within(dialog).getByRole('button', { name: /^upload$/i }));
    });

    await within(dialog).findByText(/Aurora Atlas/);
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/books\/upload$/), expect.any(Object))
    );
  });

  it('uploads an application archive and displays success feedback', async () => {
    authenticateTestUser();

    const booksPayload = [
      {
        id: 1,
        publisher: 'Dream Press',
        book_name: 'Dream Atlas',
        language: 'English',
        category: 'Fiction',
        status: 'published'
      }
    ];

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const method = (init?.method ?? 'GET').toUpperCase();

      if (url.endsWith('/books') && method === 'GET') {
        return Promise.resolve(createJsonResponse(booksPayload));
      }

      if (url.includes('/storage/apps/') && method === 'GET') {
        return Promise.resolve(createJsonResponse({ path: 'macOS/', type: 'folder', children: [] }));
      }

      if (url.endsWith('/apps/macos/upload') && method === 'POST') {
        const headers = new Headers(init?.headers as HeadersInit);
        expect(headers.get('Authorization')).toBe('Bearer test-token');
        const formData = init?.body as FormData;
        expect(formData.get('file')).toBeInstanceOf(File);
        return Promise.resolve(createJsonResponse({ platform: 'macos', version: 'abc123', files: [] }));
      }

      throw new Error(`Unexpected request to ${url}`);
    });

    renderDashboard();

    await screen.findByRole('table', { name: /books table/i });
    const user = userEvent.setup();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /upload/i }));
    });

    const dialog = screen.getByRole('dialog', { name: /upload content/i });

    await act(async () => {
      await user.click(within(dialog).getByRole('tab', { name: /application/i }));
    });

    const fileInput = within(dialog).getByTestId('upload-archive-input');

    await act(async () => {
      const archive = new File(['dummy'], 'app.zip', { type: 'application/zip' });
      await user.upload(fileInput, archive);
    });

    await act(async () => {
      await user.click(within(dialog).getByRole('button', { name: /^upload$/i }));
    });

    expect(within(dialog).getByText(/uploaded build version/i)).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/apps\/macos\/upload$/), expect.any(Object)));
  });

  it('sanitizes backend error details when an upload fails', async () => {
    authenticateTestUser();

    const booksPayload = [
      {
        id: 1,
        publisher: 'Dream Press',
        book_name: 'Dream Atlas',
        language: 'English',
        category: 'Fiction',
        status: 'published'
      }
    ];

    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    try {
      vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();
        const method = (init?.method ?? 'GET').toUpperCase();

        if (url.endsWith('/books') && method === 'GET') {
          return Promise.resolve(createJsonResponse(booksPayload));
        }

        if (url.includes('/storage/apps/') && method === 'GET') {
          return Promise.resolve(createJsonResponse({ path: 'macOS/', type: 'folder', children: [] }));
        }

        if (url.endsWith('/books/1/upload') && method === 'POST') {
          return Promise.resolve(new Response('Internal server error', { status: 500 }));
        }

        throw new Error(`Unexpected request to ${url}`);
      });

      renderDashboard();

      await screen.findByRole('table', { name: /books table/i });

      const user = userEvent.setup();

      await act(async () => {
        await user.click(screen.getByRole('button', { name: /upload/i }));
      });

      const dialog = screen.getByRole('dialog', { name: /upload content/i });
      await act(async () => {
        await user.click(within(dialog).getByRole('tab', { name: /update existing/i }));
      });
      await act(async () => {
        await user.click(within(dialog).getByLabelText(/target book/i));
      });

      const bookOption = await screen.findByRole('option', { name: /dream atlas/i });
      await act(async () => {
        await user.click(bookOption);
      });

      const fileInput = within(dialog).getByTestId('upload-archive-input');
      await act(async () => {
        const archive = new File(['dummy'], 'book.zip', { type: 'application/zip' });
        await user.upload(fileInput, archive);
      });

      await act(async () => {
        await user.click(within(dialog).getByRole('button', { name: /^upload$/i }));
      });

      expect(within(dialog).getByText(/upload failed\. please check the archive and try again\./i)).toBeInTheDocument();
    } finally {
      errorSpy.mockRestore();
    }
  });

  it('initiates soft delete for a book and refreshes data', async () => {
    authenticateTestUser();

    const booksPayloadInitial = [
      {
        id: 1,
        publisher: 'Dream Press',
        book_name: 'Dream Atlas',
        language: 'English',
        category: 'Fiction',
        status: 'published'
      }
    ];

    const booksPayloadArchived = [
      {
        id: 1,
        publisher: 'Dream Press',
        book_name: 'Dream Atlas',
        language: 'English',
        category: 'Fiction',
        status: 'archived'
      }
    ];

    const emptyTree = { path: 'macos/', type: 'folder', children: [] };
    let bookFetchCount = 0;

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const method = (init?.method ?? 'GET').toUpperCase();

      if (url.endsWith('/books') && method === 'GET') {
        bookFetchCount += 1;
        const payload = bookFetchCount === 1 ? booksPayloadInitial : booksPayloadArchived;
        return Promise.resolve(createJsonResponse(payload));
      }

      if (url.toLowerCase().includes('/storage/apps/')) {
        return Promise.resolve(createJsonResponse(emptyTree));
      }

      if (url.endsWith('/books/1') && method === 'DELETE') {
        const headers = new Headers(init?.headers as HeadersInit);
        expect(headers.get('Authorization')).toBe('Bearer test-token');
        return Promise.resolve(createJsonResponse(booksPayloadArchived[0]));
      }

      throw new Error(`Unexpected request to ${url}`);
    });

    renderDashboard();

    const booksTable = await screen.findByRole('table', { name: /books table/i });
    const cell = await within(booksTable).findByText(/dream atlas/i);
    const row = cell.closest('tr');
    expect(row).not.toBeNull();

    const deleteButton = within(row as HTMLTableRowElement).getByRole('button', {
      name: /soft-delete book dream atlas/i
    });

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
        expect.stringMatching(/\/books\/1$/),
        expect.objectContaining({ method: 'DELETE' })
      )
    );

    await waitFor(() => expect(bookFetchCount).toBeGreaterThanOrEqual(2));
    await waitFor(() =>
      expect(screen.queryByRole('dialog', { name: /confirm soft delete/i })).not.toBeInTheDocument()
    );
  });

  it('surfaces errors when application build deletion fails', async () => {
    authenticateTestUser();

    const booksPayload: unknown[] = [];
    const macAppTree = {
      path: 'macos/',
      type: 'folder',
      children: [
        {
          path: 'macos/1.0.0/',
          type: 'folder',
          children: [
            {
              path: 'macos/1.0.0/app.zip',
              type: 'file',
              size: 1024
            }
          ]
        }
      ]
    };

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const method = (init?.method ?? 'GET').toUpperCase();

      if (url.endsWith('/books') && method === 'GET') {
        return Promise.resolve(createJsonResponse(booksPayload));
      }

      if (url.toLowerCase().includes('/storage/apps/macos') && method === 'GET') {
        return Promise.resolve(createJsonResponse(macAppTree));
      }

      if (url.toLowerCase().includes('/storage/apps/windows') && method === 'GET') {
        return Promise.resolve(createJsonResponse({ path: 'windows/', type: 'folder', children: [] }));
      }

      if (url.endsWith('/apps/macos') && method === 'DELETE') {
        return Promise.resolve(new Response('failure', { status: 502 }));
      }

      throw new Error(`Unexpected request to ${url}`);
    });

    renderDashboard();

    const buildsTable = await screen.findByRole('table', { name: /application builds table/i });
    const buildRow = within(buildsTable).getAllByRole('row')[1];

    const deleteButton = within(buildRow).getByRole('button', {
      name: /soft-delete build macos\/1\.0\.0/i
    });

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
        expect.stringMatching(/\/apps\/macos$/),
        expect.objectContaining({ method: 'DELETE' })
      )
    );

    expect(await screen.findByText(/unable to complete delete request/i)).toBeInTheDocument();
  });
});
