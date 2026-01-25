import { describe, expect, it, vi } from 'vitest';

import type { ApiClient } from '../lib/api';
import type { StorageNode } from '../lib/storage';
import { createBookObjectRequest, downloadBookObject, fetchBookExplorerData } from '../lib/storage';

const createMockClient = () => {
  const get = vi.fn();

  const client: ApiClient = {
    get,
    request: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    postForm: vi.fn(),
    delete: vi.fn()
  };

  return { client, get };
};

describe('fetchBookExplorerData', () => {
  it('returns tree and config data when both requests succeed', async () => {
    const { client, get } = createMockClient();

    const tree: StorageNode = { path: 'Dream Press/Dream Atlas/', type: 'folder', children: [] };
    const config = { publisher: 'Dream Press' };

    get.mockResolvedValueOnce(tree);
    get.mockResolvedValueOnce(config);

    const result = await fetchBookExplorerData('Dream Press', 'Dream Atlas', 'token-123', 'Bearer', client);

    expect(get).toHaveBeenNthCalledWith(
      1,
      '/storage/books/Dream%20Press/Dream%20Atlas',
      expect.objectContaining({ headers: { Authorization: 'Bearer token-123' } })
    );
    expect(get).toHaveBeenNthCalledWith(
      2,
      '/storage/books/Dream%20Press/Dream%20Atlas/config',
      expect.objectContaining({ headers: { Authorization: 'Bearer token-123' } })
    );

    expect(result.tree).toEqual(tree);
    expect(result.config).toEqual(config);
    expect(result.treeError).toBeNull();
    expect(result.configError).toBeNull();
  });

  it('returns errors and null data when requests fail', async () => {
    const { client, get } = createMockClient();

    get.mockRejectedValueOnce(new Error('listing failed'));
    get.mockRejectedValueOnce('config failed');

    const result = await fetchBookExplorerData('Dream Press', 'Dream Atlas', 'token-abc', 'Bearer', client);

    expect(result.tree).toBeNull();
    expect(result.config).toBeNull();
    expect(result.treeError).toBeInstanceOf(Error);
    expect(result.treeError?.message).toBe('listing failed');
    expect(result.configError).toBeInstanceOf(Error);
    expect(result.configError?.message).toBe('config failed');
  });
});

describe('createBookObjectRequest', () => {
  it('builds a request with auth headers and encoded path', () => {
    const result = createBookObjectRequest(
      'Dream Press',
      'Dream Atlas',
      'chapters/chapter 1.mp3',
      'token-xyz'
    );

    expect(result.url).toContain('/storage/books/Dream%20Press/Dream%20Atlas/object');
    expect(result.url).toContain('path=chapters%2Fchapter%201.mp3');
    expect(result.init.headers).toEqual({ Authorization: 'Bearer token-xyz' });
    expect(result.init.method).toBe('GET');
    expect(result.init.cache).toBe('no-store');
  });

  it('includes range header when provided', () => {
    const result = createBookObjectRequest(
      'Dream Press',
      'Dream Atlas',
      'audio/theme.mp3',
      'token',
      'Bearer',
      { range: 'bytes=0-1023', cache: 'reload' }
    );

    expect(result.init.headers).toEqual({
      Authorization: 'Bearer token',
      Range: 'bytes=0-1023'
    });
    expect(result.init.cache).toBe('reload');
  });
});

describe('downloadBookObject', () => {
  it('returns a blob when the request succeeds', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('media-data', {
        status: 200,
        headers: { 'Content-Type': 'application/octet-stream' }
      })
    );

    const blob = await downloadBookObject('Dream Press', 'Dream Atlas', 'audio/theme.mp3', 'token-1');
    expect(blob).toBeInstanceOf(Blob);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/storage/books/Dream%20Press/Dream%20Atlas/object'),
      expect.objectContaining({
        method: 'GET',
        headers: { Authorization: 'Bearer token-1' },
        cache: 'no-store'
      })
    );

    fetchMock.mockRestore();
  });

  it('throws when the response is not ok', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response('nope', { status: 404 }));

    await expect(
      downloadBookObject('Dream Press', 'Dream Atlas', 'missing.mp4', 'token-2')
    ).rejects.toThrow(/Unable to download file/i);

    fetchMock.mockRestore();
  });
});
