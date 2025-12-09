import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  IconButton,
  InputAdornment,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  SelectChangeEvent,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import VisibilityIcon from '@mui/icons-material/Visibility';
import SearchIcon from '@mui/icons-material/Search';
import FilterListIcon from '@mui/icons-material/FilterList';
import ClearIcon from '@mui/icons-material/Clear';
import MenuBookIcon from '@mui/icons-material/MenuBook';

import { fetchBooks, BookRecord, softDeleteBook } from '../lib/books';
import { useAuthStore } from '../stores/auth';
import BookUploadDialog from '../components/BookUploadDialog';
import BookExplorerDrawer from '../features/books/BookExplorerDrawer';
import ActivityDetailsDialog from '../components/ActivityDetailsDialog';
import AuthenticatedImage from '../components/AuthenticatedImage';

import '../styles/page.css';

type SortDirection = 'asc' | 'desc';
type SortField = 'book_title' | 'publisher' | 'language' | 'category' | 'activity_count';

interface BookListRow {
  id: number;
  bookName: string;
  bookTitle: string;
  bookCover?: string;
  activityCount?: number;
  activityDetails?: Record<string, number>;
  totalSize?: number;
  publisher: string;
  language: string;
  category: string;
  status: string;
}

const mapBookRecords = (records: BookRecord[]): BookListRow[] =>
  records.map((record) => ({
    id: record.id,
    bookName: record.book_name,
    bookTitle: record.book_title || record.book_name,
    bookCover: record.book_cover,
    activityCount: record.activity_count,
    activityDetails: record.activity_details,
    totalSize: record.total_size,
    publisher: record.publisher,
    language: record.language,
    category: record.category || '',
    status: record.status,
    createdAt: record.created_at,
    updatedAt: record.updated_at,
  }));

const BooksPage = () => {
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType);
  const [books, setBooks] = useState<BookListRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [publisherFilter, setPublisherFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [sortField, setSortField] = useState<SortField>('book_title');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [selectedBook, setSelectedBook] = useState<BookListRow | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<BookListRow | null>(null);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [activityDialogBook, setActivityDialogBook] = useState<BookListRow | null>(null);

  const loadBooks = async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const data = await fetchBooks(token, tokenType || 'Bearer');
      setBooks(mapBookRecords(data));
    } catch (err) {
      console.error('Failed to fetch books:', err);
      setError('Failed to load books. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getBookCoverUrl = (publisher: string, bookName: string): string => {
    return `/api/storage/books/${encodeURIComponent(publisher)}/${encodeURIComponent(bookName)}/object?path=${encodeURIComponent('images/book_cover.png')}`;
  };

  useEffect(() => {
    loadBooks();
  }, [token]);

  const handleDeleteClick = (book: BookListRow) => {
    setDeleteTarget(book);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget || !token) return;

    try {
      await softDeleteBook(deleteTarget.id, token, tokenType || 'Bearer');
      await loadBooks();
      setDeleteTarget(null);
    } catch (err) {
      console.error('Failed to delete book:', err);
      setError('Failed to delete book. Please try again.');
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const handleViewContents = (book: BookListRow) => {
    setSelectedBook(book);
  };

  const handleActivityClick = (book: BookListRow) => {
    setActivityDialogBook(book);
  };

  const formatBytes = (bytes?: number): string => {
    if (typeof bytes !== 'number' || bytes === 0) return '—';
    const units = ['B', 'KB', 'MB', 'GB'];
    const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const value = bytes / Math.pow(1024, exponent);
    return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
  };

  const publishers = useMemo(() => {
    const set = new Set(books.map((b) => b.publisher));
    return Array.from(set).sort();
  }, [books]);

  const categories = useMemo(() => {
    const set = new Set(books.map((b) => b.category).filter(Boolean));
    return Array.from(set).sort();
  }, [books]);

  const filteredAndSortedBooks = useMemo(() => {
    let result = [...books];

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (book) =>
          book.bookTitle.toLowerCase().includes(query) ||
          book.bookName.toLowerCase().includes(query) ||
          book.publisher.toLowerCase().includes(query)
      );
    }

    // Apply publisher filter
    if (publisherFilter) {
      result = result.filter((book) => book.publisher === publisherFilter);
    }

    // Apply category filter
    if (categoryFilter) {
      result = result.filter((book) => book.category === categoryFilter);
    }

    // Apply sorting
    result.sort((a, b) => {
      let aVal: string | number = '';
      let bVal: string | number = '';

      switch (sortField) {
        case 'book_title':
          aVal = a.bookTitle;
          bVal = b.bookTitle;
          break;
        case 'publisher':
          aVal = a.publisher;
          bVal = b.publisher;
          break;
        case 'language':
          aVal = a.language;
          bVal = b.language;
          break;
        case 'category':
          aVal = a.category;
          bVal = b.category;
          break;
        case 'activity_count':
          aVal = a.activityCount || 0;
          bVal = b.activityCount || 0;
          break;
      }

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        const comparison = aVal.localeCompare(bVal, undefined, { sensitivity: 'base' });
        return sortDirection === 'asc' ? comparison : -comparison;
      }

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      return 0;
    });

    return result;
  }, [books, searchQuery, publisherFilter, categoryFilter, sortField, sortDirection]);

  const clearFilters = () => {
    setSearchQuery('');
    setPublisherFilter('');
    setCategoryFilter('');
  };

  const hasActiveFilters = searchQuery || publisherFilter || categoryFilter;

  return (
    <Box component="section" className="page-container">
      <Box className="page-header">
        <Box>
          <Typography variant="h4" component="h1" className="page-title">
            Books
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage your book library with search, filters, and detailed views
          </Typography>
        </Box>
        <Button variant="contained" size="large" onClick={() => setUploadDialogOpen(true)}>
          Upload Book
        </Button>
      </Box>

      {/* Search and Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
            <TextField
              placeholder="Search by title, name, or publisher..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
                endAdornment: searchQuery && (
                  <InputAdornment position="end">
                    <IconButton size="small" onClick={() => setSearchQuery('')}>
                      <ClearIcon fontSize="small" />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
              sx={{ flexGrow: 1, minWidth: 300 }}
            />

            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel>Publisher</InputLabel>
              <Select
                value={publisherFilter}
                label="Publisher"
                onChange={(e: SelectChangeEvent) => setPublisherFilter(e.target.value)}
              >
                <MenuItem value="">All Publishers</MenuItem>
                {publishers.map((pub) => (
                  <MenuItem key={pub} value={pub}>
                    {pub}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel>Category</InputLabel>
              <Select
                value={categoryFilter}
                label="Category"
                onChange={(e: SelectChangeEvent) => setCategoryFilter(e.target.value)}
              >
                <MenuItem value="">All Categories</MenuItem>
                {categories.map((cat) => (
                  <MenuItem key={cat} value={cat}>
                    {cat}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {hasActiveFilters && (
              <Button startIcon={<ClearIcon />} onClick={clearFilters}>
                Clear Filters
              </Button>
            )}
          </Stack>

          <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <FilterListIcon fontSize="small" color="action" />
            <Typography variant="body2" color="text.secondary">
              Showing {filteredAndSortedBooks.length} of {books.length} books
            </Typography>
          </Box>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell width={80}>Cover</TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortField === 'book_title'}
                    direction={sortField === 'book_title' ? sortDirection : 'asc'}
                    onClick={() => handleSort('book_title')}
                  >
                    Title
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortField === 'publisher'}
                    direction={sortField === 'publisher' ? sortDirection : 'asc'}
                    onClick={() => handleSort('publisher')}
                  >
                    Publisher
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortField === 'language'}
                    direction={sortField === 'language' ? sortDirection : 'asc'}
                    onClick={() => handleSort('language')}
                  >
                    Language
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortField === 'category'}
                    direction={sortField === 'category' ? sortDirection : 'asc'}
                    onClick={() => handleSort('category')}
                  >
                    Category
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortField === 'activity_count'}
                    direction={sortField === 'activity_count' ? sortDirection : 'asc'}
                    onClick={() => handleSort('activity_count')}
                  >
                    Activities
                  </TableSortLabel>
                </TableCell>
                <TableCell>Size</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredAndSortedBooks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 8 }}>
                    <MenuBookIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      {hasActiveFilters ? 'No books match your filters' : 'No books found'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {hasActiveFilters ? 'Try adjusting your search or filters' : 'Upload your first book to get started'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filteredAndSortedBooks.map((book) => (
                  <TableRow key={book.id} hover>
                    <TableCell>
                      <AuthenticatedImage
                        variant="rounded"
                        src={getBookCoverUrl(book.publisher, book.bookName)}
                        token={token}
                        tokenType={tokenType || 'Bearer'}
                        sx={{ width: 48, height: 48 }}
                        fallback={<MenuBookIcon />}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body1" fontWeight={500}>
                        {book.bookTitle}
                      </Typography>
                      {book.bookTitle !== book.bookName && (
                        <Typography variant="caption" color="text.secondary">
                          {book.bookName}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>{book.publisher}</TableCell>
                    <TableCell>
                      <Chip label={book.language.toUpperCase()} size="small" />
                    </TableCell>
                    <TableCell>{book.category || '—'}</TableCell>
                    <TableCell>
                      <Chip
                        label={book.activityCount || 0}
                        size="small"
                        color={book.activityCount ? 'primary' : 'default'}
                        variant="outlined"
                        onClick={() => handleActivityClick(book)}
                        sx={{ cursor: book.activityCount ? 'pointer' : 'default' }}
                      />
                    </TableCell>
                    <TableCell>{formatBytes(book.totalSize)}</TableCell>
                    <TableCell align="right">
                      <Tooltip title="View contents">
                        <IconButton size="small" onClick={() => handleViewContents(book)}>
                          <VisibilityIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete book">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteClick(book)}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Upload Dialog */}
      <BookUploadDialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        token={token}
        tokenType={tokenType}
        onSuccess={loadBooks}
      />

      {/* Book Explorer Drawer */}
      <BookExplorerDrawer
        open={!!selectedBook}
        onClose={() => setSelectedBook(null)}
        book={selectedBook}
        token={token}
        tokenType={tokenType || 'Bearer'}
      />

      {/* Activity Details Dialog */}
      <ActivityDetailsDialog
        open={!!activityDialogBook}
        onClose={() => setActivityDialogBook(null)}
        bookTitle={activityDialogBook?.bookTitle || ''}
        activityCount={activityDialogBook?.activityCount}
        activityDetails={activityDialogBook?.activityDetails}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Delete Book?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete "{deleteTarget?.bookTitle}"? This will move it to the trash.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BooksPage;
