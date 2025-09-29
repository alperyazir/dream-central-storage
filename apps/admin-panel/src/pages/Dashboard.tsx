import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
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
  Typography
} from '@mui/material';

import { fetchBooks, BookRecord } from '../lib/books';
import { SUPPORTED_APP_PLATFORMS, toPlatformSlug } from '../lib/platforms';
import { listAppContents, StorageNode } from '../lib/storage';
import { useAuthStore } from '../stores/auth';
import UploadDialog from '../components/UploadDialog';

import '../styles/page.css';

const APP_PLATFORMS = SUPPORTED_APP_PLATFORMS;

type SortDirection = 'asc' | 'desc';

type BookSortField = 'title' | 'publisher' | 'language' | 'category';

type AppSortField = 'platform' | 'version' | 'fileName' | 'path' | 'size';

interface BookRow {
  id: number;
  title: string;
  publisher: string;
  language: string;
  category: string;
}

interface AppBuildRow {
  platform: string;
  version: string;
  fileName: string;
  path: string;
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

const mapBookRecords = (records: BookRecord[]): BookRow[] =>
  records.map((record) => ({
    id: record.id,
    title: record.book_name,
    publisher: record.publisher,
    language: record.language,
    category: record.category
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
    version: entry.display,
    fileName: `${entry.display}${entry.fileCount > 1 ? ` (${entry.fileCount} files)` : ''}`,
    path: `${platformLabel}/${entry.display}`,
    size: entry.totalSize || undefined
  }));
};

const DashboardPage = () => {
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType ?? 'Bearer');
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [books, setBooks] = useState<BookRow[]>([]);
  const [appBuilds, setAppBuilds] = useState<AppBuildRow[]>([]);
  const [publisherFilter, setPublisherFilter] = useState<string>('all');
  const [bookSort, setBookSort] = useState<{ field: BookSortField; direction: SortDirection }>(
    { field: 'title', direction: 'asc' }
  );
  const [appSort, setAppSort] = useState<{ field: AppSortField; direction: SortDirection }>(
    { field: 'platform', direction: 'asc' }
  );
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [refreshIndex, setRefreshIndex] = useState(0);
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
        case 'title':
          return compareStrings(a.title, b.title) * direction;
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
        case 'path':
          return compareStrings(a.path, b.path) * direction;
        case 'size':
          return ((a.size ?? 0) - (b.size ?? 0)) * direction;
        default:
          return 0;
      }
    });

    return sorted;
  }, [appBuilds, appSort]);

  const uploadDialog = (
    <UploadDialog
      open={isUploadOpen}
      onClose={() => setIsUploadOpen(false)}
      books={books}
      platforms={APP_PLATFORMS}
      token={token}
      tokenType={tokenType}
      onSuccess={() => setRefreshIndex((value) => value + 1)}
    />
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
              <TableCell sortDirection={bookSort.field === 'title' ? bookSort.direction : false}>
                <TableSortLabel
                  active={bookSort.field === 'title'}
                  direction={bookSort.field === 'title' ? bookSort.direction : 'asc'}
                  onClick={() => toggleBookSort('title')}
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
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredBooks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  {books.length === 0 ? 'No books found.' : 'No books match the selected publisher.'}
                </TableCell>
              </TableRow>
            ) : (
              filteredBooks.map((book) => (
                <TableRow key={book.id} hover>
                  <TableCell>{book.title}</TableCell>
                  <TableCell>{book.publisher}</TableCell>
                  <TableCell>{book.language}</TableCell>
                  <TableCell>{book.category}</TableCell>
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
              <TableCell sortDirection={appSort.field === 'fileName' ? appSort.direction : false}>
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
              <TableCell sortDirection={appSort.field === 'path' ? appSort.direction : false}>
                <TableSortLabel
                  active={appSort.field === 'path'}
                  direction={appSort.field === 'path' ? appSort.direction : 'asc'}
                  onClick={() => toggleAppSort('path')}
                >
                  Storage Path
                </TableSortLabel>
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
                <TableRow key={`${build.platform}-${build.path}`} hover>
                  <TableCell>{build.platform}</TableCell>
                  <TableCell>{build.version || '—'}</TableCell>
                  <TableCell>{build.fileName || '—'}</TableCell>
                  <TableCell>{formatBytes(build.size)}</TableCell>
                  <TableCell>{build.path}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {uploadDialog}
    </section>
  );
};

export default DashboardPage;
