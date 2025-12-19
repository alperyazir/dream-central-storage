import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import PublisherUploadDialog from '../components/PublisherUploadDialog';

const createJsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' }
  });

const mockPublishers = [
  {
    id: 1,
    name: 'dream-press',
    display_name: 'Dream Press',
    description: 'Test publisher',
    logo_url: null,
    contact_email: 'contact@dreampress.com',
    status: 'active' as const,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 2,
    name: 'nebula-house',
    display_name: 'Nebula House',
    description: null,
    logo_url: null,
    contact_email: null,
    status: 'active' as const,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
];

describe('PublisherUploadDialog', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders and loads publishers on open', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse(mockPublishers));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    const onClose = vi.fn();
    const onSuccess = vi.fn();

    render(
      <PublisherUploadDialog
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
      />
    );

    expect(await screen.findByRole('dialog', { name: /upload publisher content/i })).toBeInTheDocument();
    expect(screen.getByText(/select the publisher for this upload/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/publishers\/$/),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token',
        }),
      })
    );
  });

  it('shows stepper with three steps when no initial publisher', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse(mockPublishers));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    const onClose = vi.fn();
    const onSuccess = vi.fn();

    render(
      <PublisherUploadDialog
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
      />
    );

    await screen.findByRole('dialog');

    expect(screen.getByText(/select publisher/i)).toBeInTheDocument();
    expect(screen.getByText(/content type/i)).toBeInTheDocument();
    expect(screen.getByText(/select files/i)).toBeInTheDocument();
  });

  it('skips publisher step when initialPublisherId provided', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      throw new Error('Should not fetch publishers when initialPublisherId is provided');
    });

    const onClose = vi.fn();
    const onSuccess = vi.fn();

    render(
      <PublisherUploadDialog
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
        initialPublisherId={1}
      />
    );

    await screen.findByRole('dialog');

    // Should skip to content type step
    expect(screen.getByText(/select the type of content/i)).toBeInTheDocument();
    expect(screen.queryByText(/select the publisher/i)).not.toBeInTheDocument();
  });

  it('navigates through steps successfully', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse(mockPublishers));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    const onClose = vi.fn();
    const onSuccess = vi.fn();

    render(
      <PublisherUploadDialog
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
      />
    );

    const dialog = await screen.findByRole('dialog');
    const user = userEvent.setup();

    // Step 1: Select Publisher
    const publisherInput = within(dialog).getByLabelText(/publisher/i);
    await act(async () => {
      await user.click(publisherInput);
    });

    const publisherOption = await screen.findByRole('option', { name: /dream press/i });
    await act(async () => {
      await user.click(publisherOption);
    });

    const nextButton = within(dialog).getByRole('button', { name: /next/i });
    await act(async () => {
      await user.click(nextButton);
    });

    // Step 2: Select Content Type
    expect(within(dialog).getByText(/select the type of content/i)).toBeInTheDocument();

    const booksRadio = within(dialog).getByRole('radio', { name: /books/i });
    await act(async () => {
      await user.click(booksRadio);
    });

    await act(async () => {
      await user.click(within(dialog).getByRole('button', { name: /next/i }));
    });

    // Step 3: Select Files
    expect(within(dialog).getByText(/select files to upload/i)).toBeInTheDocument();
  });

  it('validates custom content type correctly', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse([]));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    const onClose = vi.fn();
    const onSuccess = vi.fn();

    render(
      <PublisherUploadDialog
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
        initialPublisherId={1}
      />
    );

    const dialog = await screen.findByRole('dialog');
    const user = userEvent.setup();

    // Select "Add New Type"
    const customRadio = within(dialog).getByRole('radio', { name: /add new type/i });
    await act(async () => {
      await user.click(customRadio);
    });

    const customInput = within(dialog).getByLabelText(/custom content type/i);
    expect(customInput).toBeInTheDocument();

    // Test invalid characters
    await act(async () => {
      await user.type(customInput, 'Invalid Type!');
    });

    expect(within(dialog).getByText(/only alphanumeric characters/i)).toBeInTheDocument();

    // Clear and test reserved name
    await act(async () => {
      await user.clear(customInput);
      await user.type(customInput, 'trash');
    });

    expect(within(dialog).getByText(/reserved name/i)).toBeInTheDocument();

    // Valid custom type
    await act(async () => {
      await user.clear(customInput);
      await user.type(customInput, 'valid-type_123');
    });

    expect(within(dialog).queryByText(/only alphanumeric characters/i)).not.toBeInTheDocument();
    expect(within(dialog).queryByText(/reserved name/i)).not.toBeInTheDocument();
  });

  it('validates file types based on content type', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse([]));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    const onClose = vi.fn();
    const onSuccess = vi.fn();

    render(
      <PublisherUploadDialog
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
        initialPublisherId={1}
      />
    );

    const dialog = await screen.findByRole('dialog');
    const user = userEvent.setup();

    // Select logos (only PNG, JPG, SVG allowed)
    const logosRadio = within(dialog).getByRole('radio', { name: /logos/i });
    await act(async () => {
      await user.click(logosRadio);
    });

    await act(async () => {
      await user.click(within(dialog).getByRole('button', { name: /next/i }));
    });

    // Verify we can upload valid file types
    const fileInput = within(dialog).getByTestId('publisher-upload-file-input');
    const validFile = new File(['content'], 'logo.png', { type: 'image/png' });

    await act(async () => {
      await user.upload(fileInput, validFile);
    });

    // Upload button should be enabled with valid file
    await waitFor(() => {
      const uploadButton = within(dialog).getByRole('button', { name: /upload/i });
      expect(uploadButton).not.toBeDisabled();
    });
  });

  it('validates file size based on content type', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse([]));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    const onClose = vi.fn();
    const onSuccess = vi.fn();

    render(
      <PublisherUploadDialog
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
        initialPublisherId={1}
      />
    );

    const dialog = await screen.findByRole('dialog');
    const user = userEvent.setup();

    // Select logos (max 5MB)
    const logosRadio = within(dialog).getByRole('radio', { name: /logos/i });
    await act(async () => {
      await user.click(logosRadio);
    });

    await act(async () => {
      await user.click(within(dialog).getByRole('button', { name: /next/i }));
    });

    // Try to upload file larger than 5MB
    const fileInput = within(dialog).getByTestId('publisher-upload-file-input');

    // Create a file object with size larger than 5MB
    const largeFile = new File(['x'.repeat(6 * 1024 * 1024)], 'large-logo.png', { type: 'image/png' });
    Object.defineProperty(largeFile, 'size', { value: 6 * 1024 * 1024 });

    await act(async () => {
      await user.upload(fileInput, largeFile);
    });

    expect(await within(dialog).findByText(/exceeds maximum size/i)).toBeInTheDocument();
  });

  it('uploads book successfully', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const method = (init?.method ?? 'GET').toUpperCase();

      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse([]));
      }

      if (url.includes('/books/upload') && method === 'POST') {
        return Promise.resolve(createJsonResponse({
          book: {
            id: 1,
            publisher_id: 1,
            book_name: 'test-book',
          },
          version: '1.0.0',
          files: [],
        }));
      }

      throw new Error(`Unexpected request to ${url}`);
    });

    const onClose = vi.fn();
    const onSuccess = vi.fn();

    render(
      <PublisherUploadDialog
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
        initialPublisherId={1}
      />
    );

    const dialog = await screen.findByRole('dialog');
    const user = userEvent.setup();

    // Select books
    const booksRadio = within(dialog).getByRole('radio', { name: /books/i });
    await act(async () => {
      await user.click(booksRadio);
    });

    await act(async () => {
      await user.click(within(dialog).getByRole('button', { name: /next/i }));
    });

    // Upload file
    const fileInput = within(dialog).getByTestId('publisher-upload-file-input');
    const bookFile = new File(['content'], 'book.zip', { type: 'application/zip' });

    await act(async () => {
      await user.upload(fileInput, bookFile);
    });

    await act(async () => {
      await user.click(within(dialog).getByRole('button', { name: /upload/i }));
    });

    await waitFor(() => {
      expect(within(dialog).getByText(/upload completed successfully/i)).toBeInTheDocument();
    });

    expect(onSuccess).toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/books\/upload$/),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('displays error when upload fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    try {
      vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();
        const method = (init?.method ?? 'GET').toUpperCase();

        if (url.endsWith('/publishers/')) {
          return Promise.resolve(createJsonResponse([]));
        }

        if (url.includes('/books/upload') && method === 'POST') {
          return Promise.resolve(new Response('Upload failed', { status: 500 }));
        }

        throw new Error(`Unexpected request to ${url}`);
      });

      const onClose = vi.fn();
      const onSuccess = vi.fn();

      render(
        <PublisherUploadDialog
          open={true}
          onClose={onClose}
          onSuccess={onSuccess}
          token="test-token"
          tokenType="Bearer"
          initialPublisherId={1}
        />
      );

      const dialog = await screen.findByRole('dialog');
      const user = userEvent.setup();

      // Select books and proceed
      const booksRadio = within(dialog).getByRole('radio', { name: /books/i });
      await act(async () => {
        await user.click(booksRadio);
      });

      await act(async () => {
        await user.click(within(dialog).getByRole('button', { name: /next/i }));
      });

      // Upload file
      const fileInput = within(dialog).getByTestId('publisher-upload-file-input');
      const bookFile = new File(['content'], 'book.zip', { type: 'application/zip' });

      await act(async () => {
        await user.upload(fileInput, bookFile);
      });

      await act(async () => {
        await user.click(within(dialog).getByRole('button', { name: /upload/i }));
      });

      expect(await within(dialog).findByText(/upload failed/i)).toBeInTheDocument();
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });

  it('prevents upload when no publisher selected', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse(mockPublishers));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    const onClose = vi.fn();
    const onSuccess = vi.fn();

    render(
      <PublisherUploadDialog
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
      />
    );

    const dialog = await screen.findByRole('dialog');

    // Try to proceed without selecting publisher
    const nextButton = within(dialog).getByRole('button', { name: /next/i });
    expect(nextButton).toBeDisabled();
  });

  it('prevents upload when no content type selected', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse([]));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    const onClose = vi.fn();
    const onSuccess = vi.fn();

    render(
      <PublisherUploadDialog
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
        initialPublisherId={1}
      />
    );

    const dialog = await screen.findByRole('dialog');

    // Next button should be disabled without content type selection
    const nextButton = within(dialog).getByRole('button', { name: /next/i });
    expect(nextButton).toBeDisabled();
  });

  it('prevents upload when no files selected', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse([]));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    const onClose = vi.fn();
    const onSuccess = vi.fn();

    render(
      <PublisherUploadDialog
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
        initialPublisherId={1}
      />
    );

    const dialog = await screen.findByRole('dialog');
    const user = userEvent.setup();

    // Select content type and proceed
    const booksRadio = within(dialog).getByRole('radio', { name: /books/i });
    await act(async () => {
      await user.click(booksRadio);
    });

    const nextButton = within(dialog).getByRole('button', { name: /next/i });
    await act(async () => {
      await user.click(nextButton);
    });

    // Upload button should be disabled without files
    const uploadButton = within(dialog).getByRole('button', { name: /upload/i });
    expect(uploadButton).toBeDisabled();
  });

  it('resets state when dialog closes', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse(mockPublishers));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    const onClose = vi.fn();
    const onSuccess = vi.fn();

    const { rerender } = render(
      <PublisherUploadDialog
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
      />
    );

    await screen.findByRole('dialog');

    // Close the dialog
    rerender(
      <PublisherUploadDialog
        open={false}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
      />
    );

    // Re-open should reset to first step
    rerender(
      <PublisherUploadDialog
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
      />
    );

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText(/select the publisher for this upload/i)).toBeInTheDocument();
  });

  it('shows error when asset upload endpoint is not implemented', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    try {
      vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
        const url = input.toString();
        if (url.endsWith('/publishers/')) {
          return Promise.resolve(createJsonResponse([]));
        }
        throw new Error(`Unexpected request to ${url}`);
      });

      const onClose = vi.fn();
      const onSuccess = vi.fn();

      render(
        <PublisherUploadDialog
          open={true}
          onClose={onClose}
          onSuccess={onSuccess}
          token="test-token"
          tokenType="Bearer"
          initialPublisherId={1}
        />
      );

      const dialog = await screen.findByRole('dialog');
      const user = userEvent.setup();

      // Select materials (not books)
      const materialsRadio = within(dialog).getByRole('radio', { name: /materials/i });
      await act(async () => {
        await user.click(materialsRadio);
      });

      await act(async () => {
        await user.click(within(dialog).getByRole('button', { name: /next/i }));
      });

      // Upload file
      const fileInput = within(dialog).getByTestId('publisher-upload-file-input');
      const pdfFile = new File(['content'], 'material.pdf', { type: 'application/pdf' });

      await act(async () => {
        await user.upload(fileInput, pdfFile);
      });

      await act(async () => {
        await user.click(within(dialog).getByRole('button', { name: /upload/i }));
      });

      expect(await within(dialog).findByText(/story 9.4 required/i)).toBeInTheDocument();
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });

  it('allows navigation back through steps', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith('/publishers/')) {
        return Promise.resolve(createJsonResponse(mockPublishers));
      }
      throw new Error(`Unexpected request to ${url}`);
    });

    const onClose = vi.fn();
    const onSuccess = vi.fn();

    render(
      <PublisherUploadDialog
        open={true}
        onClose={onClose}
        onSuccess={onSuccess}
        token="test-token"
        tokenType="Bearer"
      />
    );

    const dialog = await screen.findByRole('dialog');
    const user = userEvent.setup();

    // Go to step 2
    const publisherInput = within(dialog).getByLabelText(/publisher/i);
    await act(async () => {
      await user.click(publisherInput);
    });

    const publisherOption = await screen.findByRole('option', { name: /dream press/i });
    await act(async () => {
      await user.click(publisherOption);
    });

    await act(async () => {
      await user.click(within(dialog).getByRole('button', { name: /next/i }));
    });

    // Verify we're on step 2
    expect(within(dialog).getByText(/select the type of content/i)).toBeInTheDocument();

    // Go back to step 1
    await act(async () => {
      await user.click(within(dialog).getByRole('button', { name: /back/i }));
    });

    // Verify we're back on step 1
    expect(within(dialog).getByText(/select the publisher for this upload/i)).toBeInTheDocument();
  });
});
