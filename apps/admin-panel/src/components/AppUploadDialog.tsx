import { ChangeEvent, useState } from 'react';
import {
  Alert,
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
  Typography
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

import { uploadAppArchive } from '../lib/uploads';
import { ApiError } from '../lib/api';

interface AppUploadDialogProps {
  open: boolean;
  onClose: () => void;
  platforms: readonly string[];
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

const AppUploadDialog = ({ open, onClose, platforms, token, tokenType, onSuccess }: AppUploadDialogProps) => {
  const [file, setFile] = useState<File | null>(null);
  const [platform, setPlatform] = useState('');
  const [uploading, setUploading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setFeedback(null);
    }
  };

  const handlePlatformChange = (event: SelectChangeEvent) => {
    setPlatform(event.target.value);
    setFeedback(null);
  };

  const handleUpload = async () => {
    if (!file || !token || !platform) {
      setFeedback({ type: 'error', message: 'Please select a file and platform' });
      return;
    }

    setUploading(true);
    setFeedback(null);

    try {
      await uploadAppArchive(platform, file, token, tokenType || 'Bearer');
      setFeedback({ type: 'success', message: 'App uploaded successfully!' });
      setFile(null);
      setPlatform('');
      onSuccess();

      setTimeout(() => {
        onClose();
        setFeedback(null);
      }, 1500);
    } catch (error) {
      setFeedback({ type: 'error', message: deriveErrorMessage(error) });
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => {
    if (!uploading) {
      setFile(null);
      setPlatform('');
      setFeedback(null);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Upload Application</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Select a ZIP archive containing your application build.
        </Typography>

        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Platform</InputLabel>
          <Select
            value={platform}
            label="Platform"
            onChange={handlePlatformChange}
            disabled={uploading}
          >
            {platforms.map((p) => (
              <MenuItem key={p} value={p}>
                {p}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Button
          component="label"
          variant="outlined"
          startIcon={<CloudUploadIcon />}
          fullWidth
          disabled={uploading}
          sx={{ mb: 2 }}
        >
          {file ? file.name : 'Choose ZIP File'}
          <input
            type="file"
            accept=".zip"
            hidden
            onChange={handleFileChange}
            disabled={uploading}
          />
        </Button>

        {uploading && <LinearProgress sx={{ mb: 2 }} />}

        {feedback && (
          <Alert severity={feedback.type} sx={{ mt: 2 }}>
            {feedback.message}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={uploading}>
          Cancel
        </Button>
        <Button
          onClick={handleUpload}
          variant="contained"
          disabled={!file || !platform || uploading}
        >
          {uploading ? 'Uploading...' : 'Upload'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AppUploadDialog;
