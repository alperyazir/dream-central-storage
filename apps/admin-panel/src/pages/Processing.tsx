import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Collapse,
  FormControl,
  IconButton,
  InputAdornment,
  InputLabel,
  LinearProgress,
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
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import RefreshIcon from '@mui/icons-material/Refresh';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import ClearIcon from '@mui/icons-material/Clear';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import QueueIcon from '@mui/icons-material/Queue';

import {
  BookWithProcessingStatus,
  BulkReprocessRequest,
  ExtendedProcessingStatus,
  ProcessingQueueItem,
  bulkReprocess,
  clearProcessingError,
  getBooksWithProcessingStatus,
  getExtendedStatusColor,
  getExtendedStatusLabel,
  getProcessingQueue,
} from '../lib/processing';
import { useAuthStore } from '../stores/auth';
import ProcessingDialog from '../components/ProcessingDialog';
import { ApiError } from '../lib/api';

import '../styles/page.css';

const STATUS_OPTIONS: { value: ExtendedProcessingStatus | ''; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'not_started', label: 'Not Started' },
  { value: 'queued', label: 'Queued' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'partial', label: 'Partial' },
];

const ProcessingPage = () => {
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType);

  // Books state
  const [books, setBooks] = useState<BookWithProcessingStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Queue state
  const [queue, setQueue] = useState<ProcessingQueueItem[]>([]);
  const [queueStats, setQueueStats] = useState({ queued: 0, processing: 0 });
  const [queueExpanded, setQueueExpanded] = useState(true);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<ExtendedProcessingStatus | ''>('');

  // Selection
  const [selectedBooks, setSelectedBooks] = useState<Set<number>>(new Set());

  // Processing dialog
  const [processingDialogOpen, setProcessingDialogOpen] = useState(false);
  const [selectedBookForProcessing, setSelectedBookForProcessing] = useState<BookWithProcessingStatus | null>(null);

  // Bulk processing
  const [bulkProcessing, setBulkProcessing] = useState(false);
  const [bulkResult, setBulkResult] = useState<{ triggered: number; skipped: number; errors: string[] } | null>(null);

  // Success message
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Fetch books
  const fetchBooks = useCallback(async () => {
    if (!token) return;

    try {
      const response = await getBooksWithProcessingStatus(token, tokenType || 'Bearer', {
        status: statusFilter || undefined,
        search: searchQuery || undefined,
      });
      setBooks(response.books);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Failed to fetch books: ${err.status}`);
      } else {
        setError('Failed to fetch books');
      }
    }
  }, [token, tokenType, statusFilter, searchQuery]);

  // Fetch queue
  const fetchQueue = useCallback(async () => {
    if (!token) return;

    try {
      const response = await getProcessingQueue(token, tokenType || 'Bearer');
      setQueue(response.queue);
      setQueueStats({
        queued: response.total_queued,
        processing: response.total_processing,
      });
    } catch (err) {
      console.error('Failed to fetch queue:', err);
    }
  }, [token, tokenType]);

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchBooks(), fetchQueue()]);
      setLoading(false);
    };
    loadData();
  }, [fetchBooks, fetchQueue]);

  // Auto-refresh when jobs are active
  useEffect(() => {
    if (queueStats.queued + queueStats.processing === 0) return;

    const interval = setInterval(() => {
      fetchBooks();
      fetchQueue();
    }, 10000);

    return () => clearInterval(interval);
  }, [queueStats, fetchBooks, fetchQueue]);

  // Handle refresh
  const handleRefresh = async () => {
    setLoading(true);
    await Promise.all([fetchBooks(), fetchQueue()]);
    setLoading(false);
  };

  // Handle select all
  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      setSelectedBooks(new Set(books.map((b) => b.book_id)));
    } else {
      setSelectedBooks(new Set());
    }
  };

  // Handle select one
  const handleSelectBook = (bookId: number) => {
    const newSelected = new Set(selectedBooks);
    if (newSelected.has(bookId)) {
      newSelected.delete(bookId);
    } else {
      newSelected.add(bookId);
    }
    setSelectedBooks(newSelected);
  };

  // Handle open processing dialog
  const handleOpenProcessing = (book: BookWithProcessingStatus) => {
    setSelectedBookForProcessing(book);
    setProcessingDialogOpen(true);
  };

  // Handle close processing dialog
  const handleCloseProcessing = () => {
    setProcessingDialogOpen(false);
    setSelectedBookForProcessing(null);
    // Refresh data after dialog closes
    handleRefresh();
  };

  // Handle clear error
  const handleClearError = async (bookId: number) => {
    if (!token) return;

    try {
      await clearProcessingError(bookId, token, tokenType || 'Bearer');
      setSuccessMessage('Error cleared successfully');
      fetchBooks();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Failed to clear error: ${err.status}`);
      } else {
        setError('Failed to clear error');
      }
    }
  };

  // Handle bulk reprocess
  const handleBulkReprocess = async () => {
    if (!token || selectedBooks.size === 0) return;

    setBulkProcessing(true);
    setBulkResult(null);

    try {
      const request: BulkReprocessRequest = {
        book_ids: Array.from(selectedBooks),
        job_type: 'full',  // Use new chunked approach
        priority: 'normal',
      };
      const response = await bulkReprocess(request, token, tokenType || 'Bearer');
      setBulkResult({
        triggered: response.triggered,
        skipped: response.skipped,
        errors: response.errors,
      });
      setSelectedBooks(new Set());
      fetchBooks();
      fetchQueue();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Bulk reprocess failed: ${err.status}`);
      } else {
        setError('Bulk reprocess failed');
      }
    } finally {
      setBulkProcessing(false);
    }
  };

  // Filtered books (client-side search if API doesn't support it yet)
  const filteredBooks = useMemo(() => {
    if (!searchQuery) return books;
    const query = searchQuery.toLowerCase();
    return books.filter(
      (b) =>
        b.book_title.toLowerCase().includes(query) ||
        b.book_name.toLowerCase().includes(query) ||
        b.publisher_name.toLowerCase().includes(query)
    );
  }, [books, searchQuery]);

  const isAllSelected = filteredBooks.length > 0 && selectedBooks.size === filteredBooks.length;
  const hasActiveJobs = queueStats.queued + queueStats.processing > 0;

  return (
    <Box className="page-container">
      <Box className="page-header">
        <Typography variant="h4" component="h1">
          AI Processing Dashboard
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            color="primary"
            onClick={handleBulkReprocess}
            disabled={selectedBooks.size === 0 || bulkProcessing}
            startIcon={bulkProcessing ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
          >
            Bulk Reprocess ({selectedBooks.size})
          </Button>
          <Button
            variant="outlined"
            onClick={handleRefresh}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : <RefreshIcon />}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Queue Panel */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ pb: 1 }}>
          <Box
            sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
            onClick={() => setQueueExpanded(!queueExpanded)}
          >
            <Stack direction="row" spacing={2} alignItems="center">
              <QueueIcon color="primary" />
              <Typography variant="h6">Processing Queue</Typography>
              <Chip
                label={`${queueStats.queued} queued`}
                size="small"
                color={queueStats.queued > 0 ? 'info' : 'default'}
              />
              <Chip
                label={`${queueStats.processing} processing`}
                size="small"
                color={queueStats.processing > 0 ? 'primary' : 'default'}
              />
              {hasActiveJobs && (
                <Typography variant="caption" color="text.secondary">
                  (Auto-refreshing every 10s)
                </Typography>
              )}
            </Stack>
            <IconButton size="small">
              {queueExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
        </CardContent>
        <Collapse in={queueExpanded}>
          <CardContent sx={{ pt: 0 }}>
            {queue.length === 0 ? (
              <Typography color="text.secondary">No jobs in queue</Typography>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>#</TableCell>
                      <TableCell>Book</TableCell>
                      <TableCell>Publisher</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Progress</TableCell>
                      <TableCell>Step</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {queue.slice(0, 5).map((item) => (
                      <TableRow key={item.job_id}>
                        <TableCell>{item.position}</TableCell>
                        <TableCell>{item.book_title || item.book_name}</TableCell>
                        <TableCell>{item.publisher_name}</TableCell>
                        <TableCell>
                          <Chip
                            label={item.status === 'queued' ? 'Queued' : 'Processing'}
                            size="small"
                            color={item.status === 'queued' ? 'info' : 'primary'}
                          />
                        </TableCell>
                        <TableCell sx={{ width: 120 }}>
                          <LinearProgress variant="determinate" value={item.progress} sx={{ height: 6, borderRadius: 3 }} />
                        </TableCell>
                        <TableCell>{item.current_step || '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Collapse>
      </Card>

      {/* Alerts */}
      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {successMessage && (
        <Alert severity="success" onClose={() => setSuccessMessage(null)} sx={{ mb: 2 }}>
          {successMessage}
        </Alert>
      )}
      {bulkResult && (
        <Alert
          severity={bulkResult.errors.length > 0 ? 'warning' : 'success'}
          onClose={() => setBulkResult(null)}
          sx={{ mb: 2 }}
        >
          Bulk reprocess: {bulkResult.triggered} triggered, {bulkResult.skipped} skipped
          {bulkResult.errors.length > 0 && ` (${bulkResult.errors.length} errors)`}
        </Alert>
      )}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <TextField
            size="small"
            placeholder="Search by title or publisher..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            sx={{ minWidth: 300 }}
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
          />
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e: SelectChangeEvent) => setStatusFilter(e.target.value as ExtendedProcessingStatus | '')}
            >
              {STATUS_OPTIONS.map((opt) => (
                <MenuItem key={opt.value} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Typography variant="body2" color="text.secondary">
            {filteredBooks.length} books
          </Typography>
        </Stack>
      </Paper>

      {/* Books Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  checked={isAllSelected}
                  indeterminate={selectedBooks.size > 0 && !isAllSelected}
                  onChange={handleSelectAll}
                />
              </TableCell>
              <TableCell>Book</TableCell>
              <TableCell>Publisher</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Progress</TableCell>
              <TableCell>Current Step</TableCell>
              <TableCell>Error</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading && filteredBooks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                  <CircularProgress />
                </TableCell>
              </TableRow>
            ) : filteredBooks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">No books found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              filteredBooks.map((book) => (
                <TableRow key={book.book_id} hover>
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={selectedBooks.has(book.book_id)}
                      onChange={() => handleSelectBook(book.book_id)}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {book.book_title || book.book_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {book.book_name}
                    </Typography>
                  </TableCell>
                  <TableCell>{book.publisher_name}</TableCell>
                  <TableCell>
                    <Chip
                      label={getExtendedStatusLabel(book.processing_status)}
                      size="small"
                      color={getExtendedStatusColor(book.processing_status)}
                    />
                  </TableCell>
                  <TableCell sx={{ width: 120 }}>
                    {book.processing_status === 'processing' || book.processing_status === 'queued' ? (
                      <LinearProgress variant="determinate" value={book.progress} sx={{ height: 6, borderRadius: 3 }} />
                    ) : book.processing_status === 'completed' ? (
                      <Typography variant="caption" color="success.main">
                        100%
                      </Typography>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">{book.current_step || '-'}</Typography>
                  </TableCell>
                  <TableCell>
                    {book.error_message ? (
                      <Tooltip title={book.error_message}>
                        <Stack direction="row" spacing={0.5} alignItems="center">
                          <ErrorOutlineIcon color="error" fontSize="small" />
                          <Typography
                            variant="caption"
                            color="error"
                            sx={{ maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                          >
                            {book.error_message}
                          </Typography>
                        </Stack>
                      </Tooltip>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1}>
                      <Tooltip title="Process">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => handleOpenProcessing(book)}
                          disabled={book.processing_status === 'processing' || book.processing_status === 'queued'}
                        >
                          <PlayArrowIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      {book.processing_status === 'failed' && (
                        <Tooltip title="Clear Error">
                          <IconButton size="small" color="warning" onClick={() => handleClearError(book.book_id)}>
                            <ClearIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Processing Dialog */}
      {selectedBookForProcessing && (
        <ProcessingDialog
          open={processingDialogOpen}
          onClose={handleCloseProcessing}
          bookId={selectedBookForProcessing.book_id}
          bookTitle={selectedBookForProcessing.book_title || selectedBookForProcessing.book_name}
          token={token}
          tokenType={tokenType}
        />
      )}
    </Box>
  );
};

export default ProcessingPage;
