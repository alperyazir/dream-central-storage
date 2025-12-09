import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
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
import MenuBookIcon from '@mui/icons-material/MenuBook';
import AppsIcon from '@mui/icons-material/Apps';
import FolderIcon from '@mui/icons-material/Folder';
import StorageIcon from '@mui/icons-material/Storage';

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
    bookTitle: record.book_title || record.book_name,
    bookCover: record.book_cover,
    activityCount: record.activity_count,
    publisher: record.publisher,
    language: record.language,
    category: record.category || '',
    status: record.status,
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

  const totalBookSize = useMemo(() => {
    // This would need actual size data from books - placeholder for now
    return 0;
  }, [books]);

  const totalAppSize = useMemo(() => {
    return appBuilds.reduce((acc, build) => acc + (build.size || 0), 0);
  }, [appBuilds]);

  const formatBytes = (bytes: number | undefined) => {
    if (!bytes || bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const value = bytes / Math.pow(1024, exponent);
    return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
  };

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

      {/* Summary Cards */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr 1fr' }, gap: 3, mb: 4 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box
                  sx={{
                    bgcolor: 'primary.main',
                    color: 'primary.contrastText',
                    p: 1.5,
                    borderRadius: 2,
                    display: 'flex'
                  }}
                >
                  <MenuBookIcon fontSize="medium" />
                </Box>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="h4" component="div" fontWeight={700}>
                    {books.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Books
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>

        <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box
                  sx={{
                    bgcolor: 'secondary.main',
                    color: 'secondary.contrastText',
                    p: 1.5,
                    borderRadius: 2,
                    display: 'flex'
                  }}
                >
                  <AppsIcon fontSize="medium" />
                </Box>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="h4" component="div" fontWeight={700}>
                    {appBuilds.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    App Builds
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>

        <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box
                  sx={{
                    bgcolor: 'success.main',
                    color: 'white',
                    p: 1.5,
                    borderRadius: 2,
                    display: 'flex'
                  }}
                >
                  <FolderIcon fontSize="medium" />
                </Box>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="h4" component="div" fontWeight={700}>
                    {uniquePublishers.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Publishers
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>

        <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box
                  sx={{
                    bgcolor: 'warning.main',
                    color: 'white',
                    p: 1.5,
                    borderRadius: 2,
                    display: 'flex'
                  }}
                >
                  <StorageIcon fontSize="medium" />
                </Box>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="h4" component="div" fontWeight={700}>
                    {formatBytes(totalAppSize)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Storage
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
      </Box>
    </section>
  );
};

export default DashboardPage;
