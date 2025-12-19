import { ChangeEvent, useEffect, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  LinearProgress,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InfoIcon from '@mui/icons-material/Info';

import { uploadTeacherMaterial, listUniqueTeacherIds } from '../lib/teachers';

interface TeacherUploadDialogProps {
  open: boolean;
  onClose: () => void;
  token: string | null;
  tokenType: string | null;
  onSuccess: () => void;
  initialTeacherId?: string;
}

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

const ALLOWED_TYPES = [
  'application/pdf',
  'text/plain',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'audio/mpeg',
  'audio/wav',
  'audio/ogg',
  'audio/mp4',
  'video/mp4',
  'video/webm',
  'video/quicktime',
];

const ACCEPT_STRING = ALLOWED_TYPES.join(',');

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, exponent);
  return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
};

const isValidTeacherId = (id: string): boolean => {
  if (!id || !id.trim()) return false;
  // Alphanumeric, underscores, hyphens only
  return /^[a-zA-Z0-9_-]+$/.test(id.trim());
};

const TeacherUploadDialog = ({
  open,
  onClose,
  token,
  tokenType,
  onSuccess,
  initialTeacherId,
}: TeacherUploadDialogProps) => {
  const [teacherId, setTeacherId] = useState(initialTeacherId || '');
  const [teacherIds, setTeacherIds] = useState<string[]>([]);
  const [loadingTeachers, setLoadingTeachers] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [fileSizeError, setFileSizeError] = useState<string | null>(null);
  const [teacherIdError, setTeacherIdError] = useState<string | null>(null);

  useEffect(() => {
    if (open && token) {
      setLoadingTeachers(true);
      listUniqueTeacherIds(token, tokenType || 'Bearer')
        .then(setTeacherIds)
        .catch((err) => console.error('Failed to load teacher IDs:', err))
        .finally(() => setLoadingTeachers(false));
    }
  }, [open, token, tokenType]);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      // Validate file size
      if (selectedFile.size > MAX_FILE_SIZE) {
        setFileSizeError(`File size (${formatBytes(selectedFile.size)}) exceeds maximum allowed size of 100MB`);
        setFile(null);
        return;
      }

      // Validate file type
      if (!ALLOWED_TYPES.includes(selectedFile.type)) {
        setFileSizeError(`File type '${selectedFile.type || 'unknown'}' is not allowed`);
        setFile(null);
        return;
      }

      setFile(selectedFile);
      setFileSizeError(null);
      setFeedback(null);
    }
  };

  const handleTeacherIdChange = (value: string) => {
    setTeacherId(value);
    if (value && !isValidTeacherId(value)) {
      setTeacherIdError('Teacher ID can only contain letters, numbers, underscores, and hyphens');
    } else if (value && value.trim()) {
      setTeacherIdError(null);
    }
  };

  const handleUpload = async () => {
    if (!file || !token || !teacherId.trim()) {
      setFeedback({ type: 'error', message: 'Please enter a teacher ID and select a file' });
      return;
    }

    if (!isValidTeacherId(teacherId)) {
      setFeedback({ type: 'error', message: 'Invalid teacher ID format' });
      return;
    }

    setUploading(true);
    setFeedback(null);

    try {
      await uploadTeacherMaterial(teacherId.trim(), file, token, tokenType || 'Bearer');
      setFeedback({ type: 'success', message: 'Material uploaded successfully!' });
      setFile(null);
      setTeacherId(initialTeacherId || '');
      setTeacherIdError(null);
      onSuccess();

      setTimeout(() => {
        onClose();
        setFeedback(null);
      }, 1500);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Upload failed. Please try again.';
      setFeedback({ type: 'error', message });
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => {
    if (!uploading) {
      setFile(null);
      setTeacherId(initialTeacherId || '');
      setFeedback(null);
      setFileSizeError(null);
      setTeacherIdError(null);
      onClose();
    }
  };

  const canUpload = file && teacherId.trim() && isValidTeacherId(teacherId) && !fileSizeError && !teacherIdError && !uploading;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Upload Teacher Material</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Upload a file to a teacher's storage. Maximum file size: 100MB.
        </Typography>

        <Autocomplete
          freeSolo
          options={teacherIds}
          value={teacherId}
          onChange={(_, value) => handleTeacherIdChange(value || '')}
          onInputChange={(_, value) => handleTeacherIdChange(value)}
          disabled={uploading || !!initialTeacherId}
          loading={loadingTeachers}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Teacher ID"
              required
              error={!!teacherIdError}
              helperText={
                teacherIdError || (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <span>Enter an existing teacher ID or create a new one. New IDs will create a new storage namespace automatically.</span>
                    <Tooltip title="Each teacher has a separate storage namespace for their materials" arrow>
                      <InfoIcon sx={{ fontSize: 16, cursor: 'help' }} />
                    </Tooltip>
                  </Box>
                )
              }
              InputProps={{
                ...params.InputProps,
                endAdornment: (
                  <>
                    {loadingTeachers ? <CircularProgress color="inherit" size={20} /> : null}
                    {params.InputProps.endAdornment}
                  </>
                ),
              }}
            />
          )}
          sx={{ mb: 3 }}
        />

        <Box
          sx={{
            border: '2px dashed',
            borderColor: fileSizeError ? 'error.main' : 'divider',
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
            minHeight: '180px',
            '&:hover': uploading
              ? {}
              : {
                  borderColor: 'primary.main',
                  bgcolor: 'action.hover',
                },
          }}
          component="label"
        >
          <CloudUploadIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            {file ? file.name : 'Click to select file'}
          </Typography>
          {file ? (
            <Typography variant="body2" color="text.secondary">
              {formatBytes(file.size)}
            </Typography>
          ) : (
            <Typography variant="body2" color="text.secondary">
              or drag and drop here
            </Typography>
          )}
          <input
            type="file"
            accept={ACCEPT_STRING}
            hidden
            onChange={handleFileChange}
            disabled={uploading}
          />
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
          Allowed file types: PDF, TXT, DOCX, JPEG, PNG, GIF, WEBP, MP3, WAV, OGG, M4A, MP4, WEBM, MOV
        </Typography>

        {fileSizeError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {fileSizeError}
          </Alert>
        )}

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
        <Button onClick={handleUpload} variant="contained" disabled={!canUpload}>
          {uploading ? 'Uploading...' : 'Upload'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TeacherUploadDialog;
