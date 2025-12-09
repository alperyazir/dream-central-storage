import { ChangeEvent, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Typography
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';

import { uploadNewBookArchive, uploadBulkBookArchives, BulkUploadResult } from '../lib/uploads';
import { ApiError } from '../lib/api';

interface BookUploadDialogProps {
  open: boolean;
  onClose: () => void;
  token: string | null;
  tokenType: string | null;
  onSuccess: () => void;
}

const deriveErrorMessage = (error: unknown): string => {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: unknown } | null)?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    return `Upload failed (${error.status}). Please try again.`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Upload failed. Please try again.';
};

const BookUploadDialog = ({ open, onClose, token, tokenType, onSuccess }: BookUploadDialogProps) => {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [uploadResults, setUploadResults] = useState<BulkUploadResult[]>([]);
  const [overrideExisting, setOverrideExisting] = useState(false);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = event.target.files;
    if (selectedFiles && selectedFiles.length > 0) {
      setFiles(Array.from(selectedFiles));
      setFeedback(null);
      setUploadResults([]);
    }
  };

  const handleUpload = async () => {
    if (files.length === 0 || !token) {
      setFeedback({ type: 'error', message: 'Please select at least one file to upload' });
      return;
    }

    setUploading(true);
    setFeedback(null);
    setUploadResults([]);

    try {
      if (files.length === 1) {
        // Single file upload
        await uploadNewBookArchive(files[0], token, tokenType || 'Bearer', undefined, { override: overrideExisting });
        setFeedback({ type: 'success', message: 'Book uploaded successfully!' });
        setFiles([]);
        onSuccess();

        setTimeout(() => {
          onClose();
          setFeedback(null);
        }, 1500);
      } else {
        // Bulk upload
        const response = await uploadBulkBookArchives(files, token, tokenType || 'Bearer', undefined, { override: overrideExisting });
        setUploadResults(response.results);

        if (response.successful === response.total) {
          setFeedback({
            type: 'success',
            message: `Successfully uploaded ${response.successful} book${response.successful > 1 ? 's' : ''}!`
          });
        } else if (response.successful > 0) {
          setFeedback({
            type: 'success',
            message: `Uploaded ${response.successful} of ${response.total} books. ${response.failed} failed.`
          });
        } else {
          setFeedback({
            type: 'error',
            message: `Failed to upload all ${response.failed} books. See details below.`
          });
        }

        onSuccess();

        // Auto-close only if all succeeded
        if (response.successful === response.total) {
          setTimeout(() => {
            onClose();
            setFeedback(null);
            setUploadResults([]);
            setFiles([]);
          }, 2000);
        }
      }
    } catch (error) {
      setFeedback({ type: 'error', message: deriveErrorMessage(error) });
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => {
    if (!uploading) {
      setFiles([]);
      setFeedback(null);
      setUploadResults([]);
      setOverrideExisting(false);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Upload Book{files.length > 1 ? 's' : ''}</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Select one or more ZIP archives containing book content and config.json files. You can upload up to 50 books at once.
        </Typography>

        <Box
          sx={{
            border: '2px dashed',
            borderColor: 'divider',
            borderRadius: 2,
            p: 4,
            textAlign: 'center',
            bgcolor: 'background.default',
            mb: 2,
            cursor: uploading ? 'not-allowed' : 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '200px',
            '&:hover': uploading ? {} : {
              borderColor: 'primary.main',
              bgcolor: 'action.hover',
            },
          }}
          component="label"
        >
          <CloudUploadIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            {files.length > 0
              ? `${files.length} file${files.length > 1 ? 's' : ''} selected`
              : 'Click to select ZIP file(s)'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            or drag and drop here
          </Typography>
          <input
            type="file"
            accept=".zip"
            multiple
            hidden
            onChange={handleFileChange}
            disabled={uploading}
          />
        </Box>

        {files.length > 0 && !uploading && uploadResults.length === 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              Selected files:
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {files.map((file, index) => (
                <Chip key={index} label={file.name} size="small" />
              ))}
            </Box>
          </Box>
        )}

        <FormControlLabel
          control={
            <Checkbox
              checked={overrideExisting}
              onChange={(e) => setOverrideExisting(e.target.checked)}
              disabled={uploading}
            />
          }
          label={
            <Box>
              <Typography variant="body2">
                Override existing books
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Delete existing books and replace with new uploads
              </Typography>
            </Box>
          }
          sx={{ mb: 2 }}
        />

        {uploading && <LinearProgress sx={{ mb: 2 }} />}

        {uploadResults.length > 0 && (
          <Box sx={{ mt: 2, mb: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Upload Results:
            </Typography>
            <List dense>
              {uploadResults.map((result, index) => (
                <ListItem
                  key={index}
                  sx={{
                    bgcolor: result.success ? 'success.light' : 'error.light',
                    mb: 1,
                    borderRadius: 1,
                    opacity: 0.9
                  }}
                >
                  {result.success ? (
                    <CheckCircleIcon color="success" sx={{ mr: 1 }} fontSize="small" />
                  ) : (
                    <ErrorIcon color="error" sx={{ mr: 1 }} fontSize="small" />
                  )}
                  <ListItemText
                    primary={result.filename}
                    secondary={
                      result.success
                        ? `${result.publisher} / ${result.book_name}`
                        : result.error
                    }
                    primaryTypographyProps={{
                      variant: 'body2',
                      sx: { color: result.success ? 'success.dark' : 'error.dark' }
                    }}
                    secondaryTypographyProps={{
                      variant: 'caption',
                      sx: { color: result.success ? 'success.dark' : 'error.dark' }
                    }}
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {feedback && (
          <Alert severity={feedback.type} sx={{ mt: 2 }}>
            {feedback.message}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={uploading}>
          {uploadResults.length > 0 ? 'Close' : 'Cancel'}
        </Button>
        <Button
          onClick={handleUpload}
          variant="contained"
          disabled={files.length === 0 || uploading}
        >
          {uploading ? 'Uploading...' : `Upload ${files.length > 0 ? `(${files.length})` : ''}`}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default BookUploadDialog;
