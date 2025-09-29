import { ChangeEvent, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  SelectChangeEvent,
  Stack,
  Tab,
  Tabs,
  Typography
} from '@mui/material';

import { uploadAppArchive, uploadBookArchive } from '../lib/uploads';

interface UploadBookOption {
  id: number;
  title: string;
  publisher: string;
}

interface UploadDialogProps {
  open: boolean;
  onClose: () => void;
  books: UploadBookOption[];
  platforms: readonly string[];
  token: string | null;
  tokenType: string | null;
  onSuccess: () => void;
}

const FILE_ACCEPT = '.zip';

type UploadMode = 'book' | 'app';

type FeedbackState = {
  type: 'success' | 'error';
  message: string;
} | null;

const deriveErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    if (/^please select/i.test(error.message)) {
      return error.message;
    }

    if (/^upload failed/i.test(error.message)) {
      return error.message;
    }
  }

  return 'Upload failed. Please check the archive and try again.';
};

const UploadDialog = ({
  open,
  onClose,
  books,
  platforms,
  token,
  tokenType,
  onSuccess
}: UploadDialogProps) => {
  const [mode, setMode] = useState<UploadMode>('book');
  const [selectedBookId, setSelectedBookId] = useState<number | ''>('');
  const [selectedPlatform, setSelectedPlatform] = useState<string>(platforms[0] ?? '');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState>(null);

  const normalizedTokenType = tokenType ?? 'Bearer';
  const isAuthenticated = Boolean(token);

  const sortedBooks = useMemo(
    () => [...books].sort((a, b) => a.title.localeCompare(b.title, undefined, { sensitivity: 'base' })),
    [books]
  );

  useEffect(() => {
    if (!open) {
      setMode('book');
      setSelectedBookId('');
      setSelectedPlatform(platforms[0] ?? '');
      setSelectedFile(null);
      setIsSubmitting(false);
      setFeedback(null);
    }
  }, [open, platforms]);

  const handleModeChange = (_: unknown, value: UploadMode) => {
    setMode(value);
    setFeedback(null);
    setSelectedFile(null);
  };

  const handleBookChange = (event: SelectChangeEvent<string>) => {
    const value = event.target.value;
    setSelectedBookId(value ? Number(value) : '');
  };

  const handlePlatformChange = (event: SelectChangeEvent<string>) => {
    setSelectedPlatform(event.target.value);
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setFeedback(null);

    // Reset the underlying input so users can re-select the same archive consecutively.
    event.target.value = '';
  };

  const selectedBook = mode === 'book' && selectedBookId
    ? sortedBooks.find((book) => book.id === selectedBookId)
    : undefined;

  const canUpload =
    isAuthenticated &&
    selectedFile !== null &&
    !isSubmitting &&
    (mode === 'book' ? selectedBookId !== '' : Boolean(selectedPlatform));

  const handleUpload = async () => {
    if (!token || !selectedFile) {
      return;
    }

    setIsSubmitting(true);
    setFeedback(null);

    try {
      if (mode === 'book') {
        if (!selectedBookId) {
          throw new Error('Please select a book to upload.');
        }

        const response = await uploadBookArchive(selectedBookId, selectedFile, token, normalizedTokenType);
        const fileLabel = response.files.length === 1 ? 'file' : 'files';
        setFeedback({
          type: 'success',
          message: `Uploaded ${response.files.length} ${fileLabel} for “${selectedBook?.title ?? 'book'}”.`
        });
      } else {
        if (!selectedPlatform) {
          throw new Error('Please select a platform to upload.');
        }

        const response = await uploadAppArchive(selectedPlatform, selectedFile, token, normalizedTokenType);
        setFeedback({
          type: 'success',
          message: `Uploaded build version ${response.version} for ${response.platform}.`
        });
      }

      setSelectedFile(null);
      onSuccess();
    } catch (error) {
      console.error('Upload failed', error);
      setFeedback({ type: 'error', message: deriveErrorMessage(error) });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      onClose();
    }
  };

  const renderBookForm = () => (
    <Stack spacing={2} sx={{ mt: 2 }}>
      <Typography variant="body2" color="text.secondary">
        Select a zipped Book Data folder (metadata, content assets, etc.) and target the catalog entry it belongs to.
        The archive is unpacked into the publisher and book path automatically.
      </Typography>
      <FormControl fullWidth size="small" disabled={sortedBooks.length === 0}>
        <InputLabel id="upload-book-select-label">Target Book</InputLabel>
        <Select
          id="upload-book-select"
          labelId="upload-book-select-label"
          value={selectedBookId === '' ? '' : String(selectedBookId)}
          label="Target Book"
          onChange={handleBookChange}
        >
          {sortedBooks.length === 0 ? (
            <MenuItem value="" disabled>
              No books available
            </MenuItem>
          ) : (
            sortedBooks.map((book) => (
              <MenuItem key={book.id} value={book.id}>
                {book.title} — {book.publisher}
              </MenuItem>
            ))
          )}
        </Select>
      </FormControl>
    </Stack>
  );

  const renderAppForm = () => (
    <Stack spacing={2} sx={{ mt: 2 }}>
      <Typography variant="body2" color="text.secondary">
        Upload a zipped application build for the chosen platform. Include the platform folder and compiled assets in
        the archive; the storage service stores it under the expected platform/version hierarchy.
      </Typography>
      <FormControl fullWidth size="small">
        <InputLabel id="upload-platform-select-label">Platform</InputLabel>
        <Select
          id="upload-platform-select"
          labelId="upload-platform-select-label"
          value={selectedPlatform}
          label="Platform"
          onChange={handlePlatformChange}
        >
          {platforms.map((platform) => (
            <MenuItem key={platform} value={platform}>
              {platform}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Stack>
  );

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
      <DialogTitle>Upload Content</DialogTitle>
      <DialogContent>
        <Tabs
          value={mode}
          onChange={handleModeChange}
          aria-label="Upload target"
          variant="fullWidth"
          sx={{ mt: 1 }}
        >
          <Tab value="book" label="Book" id="upload-tab-book" aria-controls="upload-panel-book" />
          <Tab value="app" label="Application" id="upload-tab-app" aria-controls="upload-panel-app" />
        </Tabs>

        {isSubmitting && <LinearProgress sx={{ mt: 2 }} />}

        {feedback && (
          <Alert severity={feedback.type} sx={{ mt: 2 }} onClose={() => setFeedback(null)}>
            {feedback.message}
          </Alert>
        )}

        {mode === 'book' ? renderBookForm() : renderAppForm()}

        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Archive File
          </Typography>
          <Stack direction="row" spacing={2} alignItems="center">
            <Button component="label" variant="outlined" disabled={!isAuthenticated || isSubmitting}>
              Choose File
              <input
                type="file"
                hidden
                accept={FILE_ACCEPT}
                onChange={handleFileChange}
                data-testid="upload-archive-input"
              />
            </Button>
            <Typography variant="body2" color="text.secondary">
              {selectedFile ? selectedFile.name : 'Select a .zip archive (up to backend limits).'}
            </Typography>
          </Stack>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            {mode === 'book'
              ? 'Expected layout: metadata.json at the root with content/ assets inside the archive.'
              : 'Expected layout: {platform}/{version}/build files packaged inside the archive.'}
          </Typography>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button onClick={handleUpload} variant="contained" disabled={!canUpload}>
          Upload
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default UploadDialog;
