import { describe, expect, it, vi } from 'vitest';

import type { ApiClient } from '../lib/api';
import type { Publisher, PublisherCreate, PublisherUpdate } from '../lib/publishers';
import {
  createPublisher,
  deletePublisher,
  fetchPublisher,
  fetchPublisherBooks,
  fetchPublisherByName,
  fetchPublishers,
  updatePublisher,
} from '../lib/publishers';

const createMockClient = () => {
  const get = vi.fn();
  const post = vi.fn();
  const request = vi.fn();
  const deleteFn = vi.fn();

  const client: ApiClient = {
    get,
    post,
    put: vi.fn(),
    request,
    postForm: vi.fn(),
    delete: deleteFn,
  };

  return { client, get, post, request, delete: deleteFn };
};

const mockPublisher: Publisher = {
  id: 1,
  name: 'test-publisher',
  display_name: 'Test Publisher',
  description: 'A test publisher',
  logo_url: 'https://example.com/logo.png',
  contact_email: 'contact@test.com',
  status: 'active',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

describe('fetchPublishers', () => {
  it('fetches all publishers with correct headers', async () => {
    const { client, get } = createMockClient();
    const publishers = [mockPublisher];
    get.mockResolvedValueOnce(publishers);

    const result = await fetchPublishers('token-123', 'Bearer', client);

    expect(get).toHaveBeenCalledWith('/publishers/', {
      headers: { Authorization: 'Bearer token-123' },
    });
    expect(result).toEqual(publishers);
  });

  it('handles empty publisher list', async () => {
    const { client, get } = createMockClient();
    get.mockResolvedValueOnce([]);

    const result = await fetchPublishers('token-abc', 'Bearer', client);

    expect(result).toEqual([]);
  });
});

describe('fetchPublisher', () => {
  it('fetches a single publisher by ID', async () => {
    const { client, get } = createMockClient();
    get.mockResolvedValueOnce(mockPublisher);

    const result = await fetchPublisher(1, 'token-xyz', 'Bearer', client);

    expect(get).toHaveBeenCalledWith('/publishers/1', {
      headers: { Authorization: 'Bearer token-xyz' },
    });
    expect(result).toEqual(mockPublisher);
  });

  it('throws error when publisher not found', async () => {
    const { client, get } = createMockClient();
    get.mockRejectedValueOnce(new Error('Publisher not found'));

    await expect(fetchPublisher(999, 'token', 'Bearer', client)).rejects.toThrow(
      'Publisher not found'
    );
  });
});

describe('fetchPublisherByName', () => {
  it('fetches a publisher by name with URL encoding', async () => {
    const { client, get } = createMockClient();
    get.mockResolvedValueOnce(mockPublisher);

    const result = await fetchPublisherByName('test-publisher', 'token-123', 'Bearer', client);

    expect(get).toHaveBeenCalledWith('/publishers/by-name/test-publisher', {
      headers: { Authorization: 'Bearer token-123' },
    });
    expect(result).toEqual(mockPublisher);
  });

  it('properly encodes publisher names with special characters', async () => {
    const { client, get } = createMockClient();
    get.mockResolvedValueOnce(mockPublisher);

    await fetchPublisherByName('Test & Co.', 'token', 'Bearer', client);

    expect(get).toHaveBeenCalledWith('/publishers/by-name/Test%20%26%20Co.', {
      headers: { Authorization: 'Bearer token' },
    });
  });
});

describe('createPublisher', () => {
  it('creates a new publisher with required fields', async () => {
    const { client, post } = createMockClient();
    const newPublisher: PublisherCreate = {
      name: 'new-publisher',
      display_name: 'New Publisher',
    };
    post.mockResolvedValueOnce(mockPublisher);

    const result = await createPublisher(newPublisher, 'token-create', 'Bearer', client);

    expect(post).toHaveBeenCalledWith('/publishers/', newPublisher, {
      headers: { Authorization: 'Bearer token-create' },
    });
    expect(result).toEqual(mockPublisher);
  });

  it('creates a publisher with all optional fields', async () => {
    const { client, post } = createMockClient();
    const newPublisher: PublisherCreate = {
      name: 'full-publisher',
      display_name: 'Full Publisher',
      description: 'Complete description',
      logo_url: 'https://example.com/logo.png',
      contact_email: 'contact@full.com',
      status: 'active',
    };
    post.mockResolvedValueOnce(mockPublisher);

    const result = await createPublisher(newPublisher, 'token', 'Bearer', client);

    expect(post).toHaveBeenCalledWith('/publishers/', newPublisher, {
      headers: { Authorization: 'Bearer token' },
    });
    expect(result).toEqual(mockPublisher);
  });
});

describe('updatePublisher', () => {
  it('updates a publisher with partial data', async () => {
    const { client, request } = createMockClient();
    const updates: PublisherUpdate = {
      display_name: 'Updated Name',
      description: 'Updated description',
    };
    request.mockResolvedValueOnce(mockPublisher);

    const result = await updatePublisher(1, updates, 'token-update', 'Bearer', client);

    expect(request).toHaveBeenCalledWith('/publishers/1', {
      method: 'PUT',
      headers: {
        Authorization: 'Bearer token-update',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    });
    expect(result).toEqual(mockPublisher);
  });

  it('updates publisher status', async () => {
    const { client, request } = createMockClient();
    const updates: PublisherUpdate = { status: 'inactive' };
    request.mockResolvedValueOnce({ ...mockPublisher, status: 'inactive' });

    const result = await updatePublisher(1, updates, 'token', 'Bearer', client);

    expect(result.status).toBe('inactive');
  });
});

describe('deletePublisher', () => {
  it('soft-deletes a publisher', async () => {
    const { client, delete: deleteFn } = createMockClient();
    deleteFn.mockResolvedValueOnce(undefined);

    await deletePublisher(1, 'token-delete', 'Bearer', client);

    expect(deleteFn).toHaveBeenCalledWith('/publishers/1', undefined, {
      headers: { Authorization: 'Bearer token-delete' },
    });
  });

  it('handles deletion errors', async () => {
    const { client, delete: deleteFn } = createMockClient();
    deleteFn.mockRejectedValueOnce(new Error('Cannot delete publisher'));

    await expect(deletePublisher(1, 'token', 'Bearer', client)).rejects.toThrow(
      'Cannot delete publisher'
    );
  });
});

describe('fetchPublisherBooks', () => {
  it('fetches books for a specific publisher', async () => {
    const { client, get } = createMockClient();
    const mockBooks = [
      {
        id: 1,
        publisher_id: 1,
        book_name: 'test-book',
        book_title: 'Test Book',
        book_cover: 'cover.jpg',
        activity_count: 10,
        total_size: 1024,
        language: 'en',
        category: 'fiction',
        status: 'active',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      },
    ];
    get.mockResolvedValueOnce(mockBooks);

    const result = await fetchPublisherBooks(1, 'token-books', 'Bearer', client);

    expect(get).toHaveBeenCalledWith('/publishers/1/books', {
      headers: { Authorization: 'Bearer token-books' },
    });
    expect(result).toEqual(mockBooks);
  });

  it('returns empty array when publisher has no books', async () => {
    const { client, get } = createMockClient();
    get.mockResolvedValueOnce([]);

    const result = await fetchPublisherBooks(1, 'token', 'Bearer', client);

    expect(result).toEqual([]);
  });
});
