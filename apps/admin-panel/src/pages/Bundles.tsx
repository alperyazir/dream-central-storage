import { useEffect, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  LinearProgress,
  Link,
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
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import DownloadIcon from '@mui/icons-material/Download';
import DesktopWindowsIcon from '@mui/icons-material/DesktopWindows';
import AppleIcon from '@mui/icons-material/Apple';
import ArchiveIcon from '@mui/icons-material/Archive';

import {
  AsyncBundleResponse,
  BundleInfo,
  BundleJobResult,
  createBundleAsync,
  deleteBundle,
  getBundleJobStatus,
  listBundles,
  listTemplates,
  PLATFORM_LABELS,
  StandalonePlatform,
  TemplateInfo,
} from '../lib/standaloneApps';
import { BookRecord, fetchBooks } from '../lib/books';
import { useAuthStore } from '../stores/auth';
import { ApiError } from '../lib/api';

import '../styles/page.css';

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, exponent);
  return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const getPlatformIcon = (platform: string) => {
  switch (platform) {
    case 'mac':
      return <AppleIcon fontSize="small" />;
    case 'win':
    case 'win7-8':
    case 'linux':
    default:
      return <DesktopWindowsIcon fontSize="small" />;
  }
};

const getPlatformLabel = (platform: string): string => {
  return PLATFORM_LABELS[platform as StandalonePlatform] || platform;
};

const deriveErrorMessage = (error: unknown): string => {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: unknown } | null)?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    return `Request failed (${error.status}). Please try again.`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An error occurred. Please try again.';
};

const BundlesPage = () => {
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType);

  const [bundles, setBundles] = useState<BundleInfo[]>([]);
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create bundle dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [bundlePlatform, setBundlePlatform] = useState<string>('');
  const [bundleBook, setBundleBook] = useState<BookRecord | null>(null);
  const [bundleForce, setBundleForce] = useState(false);
  const [books, setBooks] = useState<BookRecord[]>([]);
  const [loadingBooks, setLoadingBooks] = useState(false);
  const [creatingBundle, setCreatingBundle] = useState(false);
  const [bundleJobId, setBundleJobId] = useState<string | null>(null);
  const [bundleProgress, setBundleProgress] = useState(0);
  const [bundleStep, setBundleStep] = useState('');
  const [bundleResult, setBundleResult] = useState<BundleJobResult | null>(null);
  const [bundleError, setBundleError] = useState<string | null>(null);

  // Delete dialog state
  const [deleteTarget, setDeleteTarget] = useState<BundleInfo | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadData = async () => {
    if (!token) return;

    setLoading(true);
    setError(null);

    try {
      const [bundlesResponse, templatesResponse] = await Promise.all([
        listBundles(token, tokenType || 'Bearer'),
        listTemplates(token, tokenType || 'Bearer'),
      ]);
      setBundles(bundlesResponse.bundles);
      setTemplates(templatesResponse.templates);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError(deriveErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [token]);

  // Create bundle handlers
  const loadBooks = async () => {
    if (!token) return;

    setLoadingBooks(true);
    try {
      const bookList = await fetchBooks(token, tokenType || 'Bearer');
      setBooks(bookList.filter((b) => b.status === 'published'));
    } catch (err) {
      console.error('Failed to load books:', err);
    } finally {
      setLoadingBooks(false);
    }
  };

  const handleOpenCreateDialog = () => {
    setBundlePlatform('');
    setBundleBook(null);
    setBundleForce(false);
    setBundleJobId(null);
    setBundleProgress(0);
    setBundleStep('');
    setBundleResult(null);
    setBundleError(null);
    setCreateDialogOpen(true);
    loadBooks();
  };

  const handleCloseCreateDialog = () => {
    if (!creatingBundle) {
      setCreateDialogOpen(false);
      setBundlePlatform('');
      setBundleBook(null);
      setBundleForce(false);
      setBundleJobId(null);
      setBundleProgress(0);
      setBundleStep('');
      setBundleResult(null);
      setBundleError(null);
    }
  };

  const handlePlatformChange = (event: SelectChangeEvent) => {
    setBundlePlatform(event.target.value);
    setBundleError(null);
    setBundleResult(null);
  };

  const pollJobStatus = async (jobId: string) => {
    if (!token) return;

    const pollInterval = 1000; // 1 second
    const maxPolls = 600; // 10 minutes max
    let pollCount = 0;

    const poll = async () => {
      try {
        const status = await getBundleJobStatus(jobId, token, tokenType || 'Bearer');

        setBundleProgress(status.progress);
        setBundleStep(status.current_step);

        if (status.status === 'completed') {
          setBundleResult(status);
          setCreatingBundle(false);
          await loadData(); // Refresh the list
          return;
        }

        if (status.status === 'failed') {
          setBundleError(status.error_message || 'Bundle creation failed');
          setCreatingBundle(false);
          return;
        }

        // Continue polling if still processing
        pollCount++;
        if (pollCount < maxPolls && (status.status === 'queued' || status.status === 'processing')) {
          setTimeout(poll, pollInterval);
        } else if (pollCount >= maxPolls) {
          setBundleError('Bundle creation timed out');
          setCreatingBundle(false);
        }
      } catch (err) {
        console.error('Failed to poll job status:', err);
        setBundleError(deriveErrorMessage(err));
        setCreatingBundle(false);
      }
    };

    poll();
  };

  const handleCreateBundle = async () => {
    if (!bundlePlatform || !bundleBook || !token) {
      setBundleError('Please select a platform and a book');
      return;
    }

    setCreatingBundle(true);
    setBundleError(null);
    setBundleResult(null);
    setBundleProgress(0);
    setBundleStep('Queuing job...');

    try {
      const response = await createBundleAsync(
        {
          platform: bundlePlatform as 'mac' | 'win' | 'win7-8' | 'linux',
          book_id: bundleBook.id,
          force: bundleForce,
        },
        token,
        tokenType || 'Bearer'
      );

      setBundleJobId(response.job_id);
      setBundleStep('Processing...');

      // Start polling for status
      pollJobStatus(response.job_id);
    } catch (err) {
      setBundleError(deriveErrorMessage(err));
      setCreatingBundle(false);
    }
  };

  // Delete handlers
  const handleDeleteClick = (bundle: BundleInfo) => {
    setDeleteTarget(bundle);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget || !token) return;

    setDeleting(true);
    try {
      await deleteBundle(deleteTarget.object_name, token, tokenType || 'Bearer');
      await loadData();
      setDeleteTarget(null);
    } catch (err) {
      console.error('Failed to delete bundle:', err);
      setError(deriveErrorMessage(err));
    } finally {
      setDeleting(false);
    }
  };

  const handleDownload = (bundle: BundleInfo) => {
    if (bundle.download_url) {
      window.open(bundle.download_url, '_blank');
    }
  };

  // Get available platforms (only those with uploaded templates)
  const availablePlatforms = templates.map((t) => t.platform);

  return (
    <Box component="section" className="page-container">
      <Box className="page-header">
        <Box>
          <Typography variant="h4" component="h1" className="page-title">
            Bundle Management
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Create and manage standalone app bundles for books.
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenCreateDialog}
          disabled={templates.length === 0}
        >
          Create Bundle
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {templates.length === 0 && !loading && (
        <Alert severity="info" sx={{ mb: 2 }}>
          No app templates uploaded yet. Upload templates in the Applications page first.
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : bundles.length === 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Book</TableCell>
                <TableCell>Publisher</TableCell>
                <TableCell>Platform</TableCell>
                <TableCell>Size</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 8 }}>
                  <ArchiveIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary">
                    No bundles created
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Create your first bundle to get started
                  </Typography>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Book</TableCell>
                <TableCell>Publisher</TableCell>
                <TableCell>Platform</TableCell>
                <TableCell>Size</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {bundles.map((bundle) => (
                <TableRow key={bundle.object_name} hover>
                  <TableCell>
                    <Typography fontWeight="medium">{bundle.book_name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {bundle.file_name}
                    </Typography>
                  </TableCell>
                  <TableCell>{bundle.publisher_name}</TableCell>
                  <TableCell>
                    <Chip
                      icon={getPlatformIcon(bundle.platform)}
                      label={getPlatformLabel(bundle.platform)}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>{formatBytes(bundle.file_size)}</TableCell>
                  <TableCell>{formatDate(bundle.created_at)}</TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 0.5 }}>
                      <Tooltip title="Download bundle">
                        <span>
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleDownload(bundle)}
                            disabled={!bundle.download_url}
                          >
                            <DownloadIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                      <Tooltip title="Delete bundle">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteClick(bundle)}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Create Bundle Dialog */}
      <Dialog open={createDialogOpen} onClose={handleCloseCreateDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Create Standalone App Bundle</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Create a standalone app bundle by combining an app template with a book&apos;s content.
          </Typography>

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Platform</InputLabel>
            <Select
              value={bundlePlatform}
              label="Platform"
              onChange={handlePlatformChange}
              disabled={creatingBundle}
            >
              {availablePlatforms.map((p) => (
                <MenuItem key={p} value={p}>
                  {PLATFORM_LABELS[p as StandalonePlatform] || p}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Autocomplete
            options={books}
            getOptionLabel={(book) => `${book.book_name} (${book.publisher})`}
            value={bundleBook}
            onChange={(_, newValue) => {
              setBundleBook(newValue);
              setBundleError(null);
              setBundleResult(null);
            }}
            loading={loadingBooks}
            disabled={creatingBundle}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Select Book"
                InputProps={{
                  ...params.InputProps,
                  endAdornment: (
                    <>
                      {loadingBooks ? <CircularProgress color="inherit" size={20} /> : null}
                      {params.InputProps.endAdornment}
                    </>
                  ),
                }}
              />
            )}
            sx={{ mb: 2 }}
          />

          <FormControlLabel
            control={
              <Checkbox
                checked={bundleForce}
                onChange={(e) => setBundleForce(e.target.checked)}
                disabled={creatingBundle}
              />
            }
            label="Force recreate (ignore existing bundle)"
            sx={{ mb: 2 }}
          />

          {creatingBundle && (
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="body2" color="text.secondary">
                  {bundleStep || 'Processing...'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {bundleProgress}%
                </Typography>
              </Box>
              <LinearProgress variant="determinate" value={bundleProgress} />
            </Box>
          )}

          {bundleError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {bundleError}
            </Alert>
          )}

          {bundleResult && (
            <Alert severity="success" sx={{ mt: 2 }}>
              <Typography variant="body2" sx={{ mb: 1 }}>
                {bundleResult.cached ? 'Existing bundle found!' : 'Bundle created successfully!'}
              </Typography>
              {bundleResult.file_name && (
                <Typography variant="body2">
                  <strong>File:</strong> {bundleResult.file_name}
                </Typography>
              )}
              {bundleResult.file_size && (
                <Typography variant="body2">
                  <strong>Size:</strong> {formatBytes(bundleResult.file_size)}
                </Typography>
              )}
              {bundleResult.download_url && (
                <>
                  <Divider sx={{ my: 1 }} />
                  <Link href={bundleResult.download_url} target="_blank" rel="noopener">
                    Download Bundle
                  </Link>
                </>
              )}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseCreateDialog} disabled={creatingBundle}>
            {bundleResult ? 'Close' : 'Cancel'}
          </Button>
          {!bundleResult && (
            <Button
              onClick={handleCreateBundle}
              variant="contained"
              disabled={!bundlePlatform || !bundleBook || creatingBundle}
            >
              {creatingBundle ? 'Creating...' : 'Create Bundle'}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onClose={() => !deleting && setDeleteTarget(null)}>
        <DialogTitle>Delete Bundle?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete the bundle for{' '}
            <strong>{deleteTarget?.book_name}</strong> ({getPlatformLabel(deleteTarget?.platform || '')})?
            This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)} disabled={deleting}>
            Cancel
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            color="error"
            variant="contained"
            disabled={deleting}
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BundlesPage;
