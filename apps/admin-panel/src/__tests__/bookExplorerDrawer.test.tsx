import type { ComponentProps } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

vi.mock('../lib/storage', async () => {
  const actual = await vi.importActual<typeof import('../lib/storage')>('../lib/storage');
  return {
    ...actual,
    fetchBookExplorerData: vi.fn(),
    downloadBookObject: vi.fn()
  };
});

import BookExplorerDrawer from '../features/books/BookExplorerDrawer';
import type { BookListRow } from '../features/books/types';
import { downloadBookObject, fetchBookExplorerData } from '../lib/storage';

const mockedFetchExplorer = vi.mocked(fetchBookExplorerData);
const mockedDownload = vi.mocked(downloadBookObject);
const createObjectURLMock = vi.fn(() => 'blob:mock-url');
const revokeObjectURLMock = vi.fn();

const baseBook: BookListRow = {
  id: 42,
  bookName: 'Dream Atlas',
  publisher: 'Dream Press',
  language: 'English',
  category: 'Fiction',
  status: 'published',
  version: '1.0.0',
  createdAt: '2025-10-01T12:00:00Z',
  updatedAt: '2025-10-05T13:30:00Z'
};

beforeAll(() => {
  vi.stubGlobal('URL', {
    createObjectURL: createObjectURLMock,
    revokeObjectURL: revokeObjectURLMock
  });
});

afterEach(() => {
  mockedFetchExplorer.mockReset();
  mockedDownload.mockReset();
  createObjectURLMock.mockReset();
  revokeObjectURLMock.mockReset();
});

afterAll(() => {
  vi.unstubAllGlobals();
});

const renderDrawer = (overrides: Partial<ComponentProps<typeof BookExplorerDrawer>> = {}) =>
  render(
    <BookExplorerDrawer
      open
      onClose={vi.fn()}
      book={baseBook}
      token="token-123"
      tokenType="Bearer"
      {...overrides}
    />
  );

describe('BookExplorerDrawer', () => {
  it('renders metadata and file tree when explorer data loads successfully', async () => {
    mockedFetchExplorer.mockResolvedValue({
      tree: {
        path: 'Dream Press/Dream Atlas/',
        type: 'folder',
        children: [
          {
            path: 'Dream Press/Dream Atlas/chapters/',
            type: 'folder',
            children: [
              {
                path: 'Dream Press/Dream Atlas/chapters/chapter1.pdf',
                type: 'file',
                size: 1024
              }
            ]
          }
        ]
      },
      config: {
        publisher: 'Dream Press',
        book_name: 'Dream Atlas',
        language: 'English',
        category: 'Fiction',
        version: '1.0.0',
        status: 'published'
      },
      treeError: null,
      configError: null
    });

    renderDrawer();

    await waitFor(() => expect(mockedFetchExplorer).toHaveBeenCalledWith(
      baseBook.publisher,
      baseBook.bookName,
      'token-123',
      'Bearer'
    ));

    expect(await screen.findByText('Metadata')).toBeInTheDocument();
    expect(screen.getByText('Dream Press')).toBeInTheDocument();
    expect(screen.getByText('Dream Atlas')).toBeInTheDocument();
    expect(screen.getByText(/Stored Files/i)).toBeInTheDocument();
    expect(screen.getByText('chapters')).toBeInTheDocument();
    expect(screen.getByText(/chapter1\.pdf/i)).toBeInTheDocument();
  });

  it('surfaces tree and metadata errors with graceful fallbacks', async () => {
    mockedFetchExplorer.mockResolvedValue({
      tree: null,
      config: null,
      treeError: new Error('listing failed'),
      configError: new Error('config missing')
    });

    renderDrawer();

    await waitFor(() => expect(mockedFetchExplorer).toHaveBeenCalled());

    expect(await screen.findByText(/unable to load book contents/i)).toBeInTheDocument();
    expect(await screen.findByText(/unable to load config\.json metadata/i)).toBeInTheDocument();
    expect(screen.getByText(/Dream Atlas/i)).toBeInTheDocument();
    expect(screen.getByText(/Dream Press/i)).toBeInTheDocument();
  });

  it('invokes download action for selected file and shows success feedback', async () => {
    mockedFetchExplorer.mockResolvedValue({
      tree: {
        path: 'Dream Press/Dream Atlas/',
        type: 'folder',
        children: [
          {
            path: 'Dream Press/Dream Atlas/assets/',
            type: 'folder',
            children: [
              {
                path: 'Dream Press/Dream Atlas/assets/sample.txt',
                type: 'file',
                size: 512
              }
            ]
          }
        ]
      },
      config: {},
      treeError: null,
      configError: null
    });
    mockedDownload.mockResolvedValue(new Blob(['text/plain'], { type: 'text/plain' }));

    const user = userEvent.setup();
    renderDrawer();

    const fileItem = await screen.findByText(/sample\.txt/i);
    await user.click(fileItem);

    const downloadButton = await screen.findByRole('button', { name: /download file sample\.txt/i });
    await user.click(downloadButton);

    await waitFor(() => expect(mockedDownload).toHaveBeenCalled());
    const calls = mockedDownload.mock.calls;
    expect(calls[0][0]).toBe(baseBook.publisher);
    expect(calls[0][1]).toBe(baseBook.bookName);
    expect(calls[0][2]).toBe('assets/sample.txt');
    expect(calls[0][3]).toBe('token-123');
    expect(calls[0][4]).toBe('Bearer');
    expect(calls[0][5]).toMatchObject({
      range: 'bytes=0-',
      cache: 'no-store'
    });
    expect((calls[0][5] as Record<string, unknown>).signal).toBeDefined();
    expect(calls[calls.length - 1]).toEqual([
      baseBook.publisher,
      baseBook.bookName,
      'assets/sample.txt',
      'token-123',
      'Bearer'
    ]);

    expect(await screen.findByText(/downloading sample\.txt/i)).toBeInTheDocument();
  });

  it('renders an image preview when selecting a supported file', async () => {
    mockedFetchExplorer.mockResolvedValue({
      tree: {
        path: 'Dream Press/Dream Atlas/',
        type: 'folder',
        children: [
          {
            path: 'Dream Press/Dream Atlas/art/',
            type: 'folder',
            children: [
              {
                path: 'Dream Press/Dream Atlas/art/cover.png',
                type: 'file',
                size: 2048
              }
            ]
          }
        ]
      },
      config: {},
      treeError: null,
      configError: null
    });

    mockedDownload.mockResolvedValue(new Blob(['image-data'], { type: 'image/png' }));

    const user = userEvent.setup();
    renderDrawer();

    const coverFile = await screen.findByText(/cover\.png/i);
    await user.click(coverFile);

    await waitFor(() => expect(createObjectURLMock).toHaveBeenCalled());

    const image = await screen.findByRole('img', { name: /preview of cover\.png/i });
    expect(image).toBeInTheDocument();
  });

  it('renders an audio preview and requests range-enabled data', async () => {
    mockedFetchExplorer.mockResolvedValue({
      tree: {
        path: 'Dream Press/Dream Atlas/',
        type: 'folder',
        children: [
          {
            path: 'Dream Press/Dream Atlas/audio/',
            type: 'folder',
            children: [
              {
                path: 'Dream Press/Dream Atlas/audio/theme.mp3',
                type: 'file',
                size: 1024
              }
            ]
          }
        ]
      },
      config: {},
      treeError: null,
      configError: null
    });

    mockedDownload.mockResolvedValue(new Blob(['audio'], { type: 'audio/mpeg' }));

    const user = userEvent.setup();
    renderDrawer();

    const audioFile = await screen.findByText(/theme\.mp3/i);
    await user.click(audioFile);

    await waitFor(() => {
      expect(mockedDownload).toHaveBeenCalled();
      const [publisher, bookName, path, , , options] = mockedDownload.mock.calls[0];
      expect(publisher).toBe(baseBook.publisher);
      expect(bookName).toBe(baseBook.bookName);
      expect(path).toBe('audio/theme.mp3');
      expect(options).toMatchObject({ range: 'bytes=0-', cache: 'no-store' });
    });

    expect(await screen.findByLabelText(/audio preview/i)).toBeInTheDocument();
  });

  it('shows unsupported message for files without preview support', async () => {
    mockedFetchExplorer.mockResolvedValue({
      tree: {
        path: 'Dream Press/Dream Atlas/',
        type: 'folder',
        children: [
          {
            path: 'Dream Press/Dream Atlas/docs/',
            type: 'folder',
            children: [
              {
                path: 'Dream Press/Dream Atlas/docs/readme.pdf',
                type: 'file',
                size: 4096
              }
            ]
          }
        ]
      },
      config: {},
      treeError: null,
      configError: null
    });

    mockedDownload.mockResolvedValue(new Blob(['text'], { type: 'application/pdf' }));

    const user = userEvent.setup();
    renderDrawer();

    const pdfFile = await screen.findByText(/readme\.pdf/i);
    await user.click(pdfFile);

    expect(
      await screen.findByText(/preview unavailable for this file type/i)
    ).toBeInTheDocument();
    expect(mockedDownload).not.toHaveBeenCalled();
  });

  it('handles preview fetch failures gracefully', async () => {
    mockedFetchExplorer.mockResolvedValue({
      tree: {
        path: 'Dream Press/Dream Atlas/',
        type: 'folder',
        children: [
          {
            path: 'Dream Press/Dream Atlas/audio/',
            type: 'folder',
            children: [
              {
                path: 'Dream Press/Dream Atlas/audio/broken.mp3',
                type: 'file',
                size: 512
              }
            ]
          }
        ]
      },
      config: {},
      treeError: null,
      configError: null
    });

    mockedDownload.mockRejectedValue(new Error('preview failed'));

    const user = userEvent.setup();
    renderDrawer();

    const brokenFile = await screen.findByText(/broken\.mp3/i);
    await user.click(brokenFile);

    expect(
      await screen.findByText(/unable to load preview/i)
    ).toBeInTheDocument();
  });
});
