import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  SelectChangeEvent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Tooltip,
  Typography,
  Stack
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';

import { fetchBooks, BookRecord, softDeleteBook } from '../lib/books';
import { SUPPORTED_APP_PLATFORMS, toPlatformSlug } from '../lib/platforms';
import { listAppContents, StorageNode } from '../lib/storage';
import { softDeleteAppBuild } from '../lib/apps';
import { useAuthStore } from '../stores/auth';
import UploadDialog from '../components/UploadDialog';
import BookExplorerDrawer from '../features/books/BookExplorerDrawer';
import type { BookListRow } from '../features/books/types';

import '../styles/page.css';

const APP_PLATFORMS = SUPPORTED_APP_PLATFORMS;

type SortDirection = 'asc' | 'desc';

type BookSortField = 'bookName' | 'publisher' | 'language' | 'category';

type AppSortField = 'platform' | 'version' | 'fileName' | 'size';

type DeleteTarget =
  | { kind: 'book'; record: BookListRow }
  | { kind: 'app'; record: AppBuildRow };

interface AppBuildRow {
  platform: string;
  platformSlug: string;
  version: string;
  fileName: string;
  storagePath: string;
  size?: number;
}

const compareStrings = (a: string, b: string) => a.localeCompare(b, undefined, { sensitivity: 'base' });

const formatBytes = (size?: number) => {
  if (typeof size !== 'number') {
    return '—';
  }

  if (size === 0) {
    return '0 B';
  }

  const units = ['B', 'KB', 'MB', 'GB'];
  const exponent = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1);
  const value = size / Math.pow(1024, exponent);
  return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
};

const formatBuildLabel = (build: AppBuildRow) => {
  if (!build) {
    return '';
  }

  if (build.version) {
    return `${build.platform} ${build.version}`;
  }

  return build.fileName || build.platform;
};

const mapBookRecords = (records: BookRecord[]): BookListRow[] =>
  records.map((record) => ({
    id: record.id,
    bookName: record.book_name,
    publisher: record.publisher,
    language: record.language,
    category: record.category,
    status: record.status,
    version: record.version,
    createdAt: record.created_at,
    updatedAt: record.updated_at
  }));

const collectAppBuildRows = (
  root: StorageNode | undefined,
  platformLabel: string,
  platformSlug: string
): AppBuildRow[] => {
  if (!root) {
    return [];
  }

  const aggregated = new Map<string, { display: string; fileCount: number; totalSize: number }>();
  const slugPrefix = `${platformSlug}/`;

  const walk = (node: StorageNode) => {
    if (node.type === 'file') {
      const normalized = node.path.replace(/\/+$/, '');
      const lowerCased = normalized.toLowerCase();
      const relative = lowerCased.startsWith(slugPrefix)
        ? normalized.slice(slugPrefix.length)
        : normalized;
      const segments = relative.split('/').filter(Boolean);
      const rootSegment = segments[0] ?? normalized;
      const key = rootSegment.toLowerCase();
      const entry = aggregated.get(key) ?? {
        display: rootSegment,
        fileCount: 0,
        totalSize: 0
      };

      entry.fileCount += 1;
      entry.totalSize += node.size ?? 0;
      aggregated.set(key, entry);
    }

    node.children?.forEach((child) => {
      walk(child);
    });
  };

  walk(root);

  return Array.from(aggregated.values()).map((entry) => ({
    platform: platformLabel,
    platformSlug,
    version: entry.display,
    fileName: `${entry.display}${entry.fileCount > 1 ? ` (${entry.fileCount} files)` : ''}`,
    storagePath: `${platformSlug}/${entry.display}/`,
    size: entry.totalSize || undefined
  }));
};

const DashboardPage = () => {
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType ?? 'Bearer');
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [books, setBooks] = useState<BookListRow[]>([]);
  const [appBuilds, setAppBuilds] = useState<AppBuildRow[]>([]);
  const [publisherFilter, setPublisherFilter] = useState<string>('all');
  const [bookSort, setBookSort] = useState<{ field: BookSortField; direction: SortDirection }>(
    { field: 'bookName', direction: 'asc' }
  );
  const [appSort, setAppSort] = useState<{ field: AppSortField; direction: SortDirection }>(
    { field: 'platform', direction: 'asc' }
  );
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [refreshIndex, setRefreshIndex] = useState(0);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [explorerBook, setExplorerBook] = useState<BookListRow | null>(null);
  const platformCount = APP_PLATFORMS.length as number;

  useEffect(() => {
    let isSubscribed = true;

    const loadDashboardData = async () => {
      if (!isAuthenticated || !token) {
        if (isSubscribed) {
          setBooks([]);
          setAppBuilds([]);
          setLoading(false);
        }
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const [bookResponse, ...appResponses] = await Promise.all([
          fetchBooks(token, tokenType),
          ...APP_PLATFORMS.map((platform) => listAppContents(toPlatformSlug(platform), token, tokenType))
        ]);

        if (!isSubscribed) {
          return;
        }

        const bookRows = mapBookRecords(bookResponse);
        const appRows = appResponses.flatMap((tree, index) =>
          collectAppBuildRows(tree, APP_PLATFORMS[index], toPlatformSlug(APP_PLATFORMS[index]))
        );

        setBooks(bookRows);
        setAppBuilds(appRows);
      } catch (requestError) {
        if (!isSubscribed) {
          return;
        }

        const message = requestError instanceof Error ? requestError.message : 'Unable to load dashboard data.';
        setError(message);
        setBooks([]);
        setAppBuilds([]);
      } finally {
        if (isSubscribed) {
          setLoading(false);
        }
      }
    };

    void loadDashboardData();

    return () => {
      isSubscribed = false;
    };
  }, [isAuthenticated, token, tokenType, refreshIndex]);

  const handlePublisherChange = (event: SelectChangeEvent<string>) => {
    setPublisherFilter(event.target.value);
  };

  const toggleBookSort = (field: BookSortField) => {
    setBookSort((current) => ({
      field,
      direction: current.field === field && current.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const toggleAppSort = (field: AppSortField) => {
    setAppSort((current) => ({
      field,
      direction: current.field === field && current.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const promptBookDelete = (record: BookListRow) => {
    setActionError(null);
    setDeleteTarget({ kind: 'book', record });
  };

  const promptAppDelete = (record: AppBuildRow) => {
    setActionError(null);
    setDeleteTarget({ kind: 'app', record });
  };

  const closeDeleteDialog = () => {
    if (isDeleting) {
      return;
    }
    setDeleteTarget(null);
  };

  const performDelete = async () => {
    if (!deleteTarget || !token) {
      return;
    }

    setIsDeleting(true);
    setActionError(null);

    try {
      if (deleteTarget.kind === 'book') {
        await softDeleteBook(deleteTarget.record.id, token, tokenType);
      } else {
        await softDeleteAppBuild(
          deleteTarget.record.platformSlug,
          deleteTarget.record.storagePath,
          token,
          tokenType
        );
      }

      setDeleteTarget(null);
      setRefreshIndex((value) => value + 1);
    } catch (requestError) {
      if (requestError instanceof Error) {
        console.error('Failed to complete delete request', requestError);
      }
      setActionError('Unable to complete delete request.');
    } finally {
      setIsDeleting(false);
    }
  };

  const uniquePublishers = useMemo(() => {
    const values = new Set<string>();
    books.forEach((book) => {
      if (book.publisher) {
        values.add(book.publisher);
      }
    });
    return Array.from(values).sort((a, b) => compareStrings(a, b));
  }, [books]);

  const filteredBooks = useMemo(() => {
    const data = publisherFilter === 'all' ? books : books.filter((book) => book.publisher === publisherFilter);

    const sorted = [...data].sort((a, b) => {
      const direction = bookSort.direction === 'asc' ? 1 : -1;
      switch (bookSort.field) {
        case 'bookName':
          return compareStrings(a.bookName, b.bookName) * direction;
        case 'publisher':
          return compareStrings(a.publisher, b.publisher) * direction;
        case 'language':
          return compareStrings(a.language, b.language) * direction;
        case 'category':
          return compareStrings(a.category, b.category) * direction;
        default:
          return 0;
      }
    });

    return sorted;
  }, [books, publisherFilter, bookSort]);

  const sortedAppBuilds = useMemo(() => {
    const sorted = [...appBuilds].sort((a, b) => {
      const direction = appSort.direction === 'asc' ? 1 : -1;
      switch (appSort.field) {
        case 'platform':
          return compareStrings(a.platform, b.platform) * direction;
        case 'version':
          return compareStrings(a.version, b.version) * direction;
        case 'fileName':
          return compareStrings(a.fileName, b.fileName) * direction;
        case 'size':
          return ((a.size ?? 0) - (b.size ?? 0)) * direction;
        default:
          return 0;
      }
    });

    return sorted;
  }, [appBuilds, appSort]);

  const uploadBookOptions = useMemo(
    () =>
      books.map((book) => ({
        id: book.id,
        title: book.bookName,
        publisher: book.publisher
      })),
    [books]
  );

  const uploadDialog = (
    <UploadDialog
      open={isUploadOpen}
      onClose={() => setIsUploadOpen(false)}
      books={uploadBookOptions}
      platforms={APP_PLATFORMS}
      token={token}
      tokenType={tokenType}
      onSuccess={() => setRefreshIndex((value) => value + 1)}
    />
  );

  const deleteDialog = (
    <Dialog
      open={Boolean(deleteTarget)}
      onClose={closeDeleteDialog}
      aria-labelledby="delete-confirmation-title"
      aria-describedby="delete-confirmation-description"
    >
      <DialogTitle id="delete-confirmation-title">Confirm Soft Delete</DialogTitle>
      <DialogContent>
        <DialogContentText id="delete-confirmation-description">
          {deleteTarget?.kind === 'book'
            ? `Soft-delete "${deleteTarget.record.bookName}"? Its metadata will be archived and associated files moved to the trash bucket.`
            : `Soft-delete application build "${deleteTarget ? formatBuildLabel(deleteTarget.record) : ''}"? Assets will be moved to the trash bucket for restoration later.`}
        </DialogContentText>
        {actionError ? (
          <Alert severity="error" sx={{ mt: 2 }}>
            {actionError}
          </Alert>
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button onClick={closeDeleteDialog} disabled={isDeleting}>
          Cancel
        </Button>
        <Button onClick={performDelete} color="error" disabled={isDeleting}>
          {isDeleting ? 'Deleting...' : 'Delete'}
        </Button>
      </DialogActions>
    </Dialog>
  );

  const isInitialLoad = loading && books.length === 0 && appBuilds.length === 0;

  if (isInitialLoad) {
    return (
      <>
        <section className="page page--centered" aria-busy="true">
          <CircularProgress aria-label="Loading dashboard data" />
          <Typography variant="body1">Loading dashboard data…</Typography>
        </section>
        {uploadDialog}
        {deleteDialog}
      </>
    );
  }

  return (
    <section className="page" aria-live="polite" aria-busy={loading}>
      <Typography variant="h4" component="h1" gutterBottom>
        Dashboard
      </Typography>
      <Typography variant="body1" paragraph>
        Review stored content at a glance. Use the filters, sorting controls, and upload tools to keep the catalog current.
      </Typography>

      {loading ? (
        <Alert severity="info" sx={{ mb: 3 }} role="status">
          Refreshing dashboard data…
        </Alert>
      ) : null}

      {error ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      ) : null}

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <FormControl size="small" sx={{ minWidth: 220 }}>
          <InputLabel id="publisher-filter-label">Publisher</InputLabel>
          <Select
            labelId="publisher-filter-label"
            id="publisher-filter"
            value={publisherFilter}
            label="Publisher"
            onChange={handlePublisherChange}
          >
            <MenuItem value="all">All publishers</MenuItem>
            {uniquePublishers.map((publisher) => (
              <MenuItem key={publisher} value={publisher}>
                {publisher}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Typography variant="body2" color="text.secondary">
          Showing {filteredBooks.length} of {books.length} books
        </Typography>
        <Button variant="contained" onClick={() => setIsUploadOpen(true)} sx={{ ml: 'auto' }}>
          Upload
        </Button>
      </Box>

      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table aria-label="Books table">
          <TableHead>
            <TableRow>
              <TableCell sortDirection={bookSort.field === 'bookName' ? bookSort.direction : false}>
                <TableSortLabel
                  active={bookSort.field === 'bookName'}
                  direction={bookSort.field === 'bookName' ? bookSort.direction : 'asc'}
                  onClick={() => toggleBookSort('bookName')}
                >
                  Title
                </TableSortLabel>
              </TableCell>
              <TableCell sortDirection={bookSort.field === 'publisher' ? bookSort.direction : false}>
                <TableSortLabel
                  active={bookSort.field === 'publisher'}
                  direction={bookSort.field === 'publisher' ? bookSort.direction : 'asc'}
                  onClick={() => toggleBookSort('publisher')}
                >
                  Publisher
                </TableSortLabel>
              </TableCell>
              <TableCell sortDirection={bookSort.field === 'language' ? bookSort.direction : false}>
                <TableSortLabel
                  active={bookSort.field === 'language'}
                  direction={bookSort.field === 'language' ? bookSort.direction : 'asc'}
                  onClick={() => toggleBookSort('language')}
                >
                  Language
                </TableSortLabel>
              </TableCell>
              <TableCell sortDirection={bookSort.field === 'category' ? bookSort.direction : false}>
                <TableSortLabel
                  active={bookSort.field === 'category'}
                  direction={bookSort.field === 'category' ? bookSort.direction : 'asc'}
                  onClick={() => toggleBookSort('category')}
                >
                  Category
                </TableSortLabel>
              </TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredBooks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  {books.length === 0 ? 'No books found.' : 'No books match the selected publisher.'}
                </TableCell>
              </TableRow>
            ) : (
              filteredBooks.map((book) => (
                <TableRow key={book.id} hover>
                  <TableCell>{book.bookName}</TableCell>
                  <TableCell>{book.publisher}</TableCell>
                  <TableCell>{book.language}</TableCell>
                  <TableCell>{book.category}</TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      <Button
                        variant="outlined"
                        size="small"
                        onClick={() => setExplorerBook(book)}
                        disabled={!token}
                      >
                        View contents
                      </Button>
                      <Tooltip title="Soft-delete book">
                        <span>
                          <IconButton
                            size="small"
                            color="error"
                            aria-label={`Soft-delete book ${book.bookName}`}
                            onClick={() => promptBookDelete(book)}
                            disabled={isDeleting}
                          >
                            <DeleteOutlineIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="h5" component="h2" gutterBottom>
        Application Builds
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Currently tracking {appBuilds.length} build artifact{appBuilds.length === 1 ? '' : 's'} across {platformCount} platform{platformCount === 1 ? '' : 's'}.
      </Typography>

      <TableContainer component={Paper}>
        <Table aria-label="Application builds table">
          <TableHead>
            <TableRow>
              <TableCell sortDirection={appSort.field === 'platform' ? appSort.direction : false}>
                <TableSortLabel
                  active={appSort.field === 'platform'}
                  direction={appSort.field === 'platform' ? appSort.direction : 'asc'}
                  onClick={() => toggleAppSort('platform')}
                >
                  Platform
                </TableSortLabel>
              </TableCell>
              <TableCell sortDirection={appSort.field === 'version' ? appSort.direction : false}>
                <TableSortLabel
                  active={appSort.field === 'version'}
                  direction={appSort.field === 'version' ? appSort.direction : 'asc'}
                  onClick={() => toggleAppSort('version')}
                >
                  Version
                </TableSortLabel>
              </TableCell>
              <TableCell sortDirection={appSort.field === 'fileName' ? appSort.direction : false} sx={{ minWidth: 200 }}>
                <TableSortLabel
                  active={appSort.field === 'fileName'}
                  direction={appSort.field === 'fileName' ? appSort.direction : 'asc'}
                  onClick={() => toggleAppSort('fileName')}
                >
                  File
                </TableSortLabel>
              </TableCell>
              <TableCell sortDirection={appSort.field === 'size' ? appSort.direction : false}>
                <TableSortLabel
                  active={appSort.field === 'size'}
                  direction={appSort.field === 'size' ? appSort.direction : 'asc'}
                  onClick={() => toggleAppSort('size')}
                >
                  Size
                </TableSortLabel>
              </TableCell>
              <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                Actions
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedAppBuilds.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  No application builds found.
                </TableCell>
              </TableRow>
            ) : (
              sortedAppBuilds.map((build) => (
                <TableRow key={build.storagePath} hover>
                  <TableCell>{build.platform}</TableCell>
                  <TableCell>{build.version || '—'}</TableCell>
                  <TableCell>{build.fileName || '—'}</TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>{formatBytes(build.size)}</TableCell>
                  <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                    <Tooltip title="Soft-delete application build">
                      <span>
                        <IconButton
                          size="small"
                          color="error"
                          aria-label={`Soft-delete build ${formatBuildLabel(build)}`}
                          onClick={() => promptAppDelete(build)}
                          disabled={isDeleting}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {uploadDialog}
      {deleteDialog}
      <BookExplorerDrawer
        open={Boolean(explorerBook)}
        onClose={() => setExplorerBook(null)}
        book={explorerBook}
        token={token ?? null}
        tokenType={tokenType}
      />
    </section>
  );
};

export default DashboardPage;
