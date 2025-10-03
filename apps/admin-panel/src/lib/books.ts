import { ApiClient, apiClient } from './api';
import { buildAuthHeaders } from './http';

export interface BookRecord {
  id: number;
  publisher: string;
  book_name: string;
  language: string;
  category: string;
  status: string;
  version?: string;
  created_at?: string;
  updated_at?: string;
}

export const fetchBooks = (
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<BookRecord[]> => client.get<BookRecord[]>('/books', { headers: buildAuthHeaders(token, tokenType) });

export const softDeleteBook = (
  bookId: number,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<BookRecord> =>
  client.delete<BookRecord>(`/books/${bookId}`, undefined, {
    headers: buildAuthHeaders(token, tokenType)
  });
