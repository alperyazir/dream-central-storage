export interface BookListRow {
  id: number;
  bookName: string;
  bookTitle: string;
  bookCover?: string;
  activityCount?: number;
  publisher: string;
  language: string;
  category: string;
  status: string;
  createdAt?: string;
  updatedAt?: string;
}
