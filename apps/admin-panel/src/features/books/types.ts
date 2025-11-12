export interface BookListRow {
  id: number;
  bookName: string;
  publisher: string;
  language: string;
  category: string;
  status: string;
  version?: string;
  createdAt?: string;
  updatedAt?: string;
}
