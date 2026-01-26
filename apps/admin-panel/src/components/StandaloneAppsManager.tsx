import { ChangeEvent, useEffect, useState } from 'react';
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
  LinearProgress,
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
  Tooltip,
  Typography,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import DownloadIcon from '@mui/icons-material/Download';
import DesktopWindowsIcon from '@mui/icons-material/DesktopWindows';
import AppleIcon from '@mui/icons-material/Apple';
import AppsIcon from '@mui/icons-material/Apps';

import {
  deleteTemplate,
  listTemplates,
  PLATFORM_LABELS,
  STANDALONE_PLATFORMS,
  StandalonePlatform,
  TemplateInfo,
  uploadTemplate,
} from '../lib/standaloneApps';
import { useAuthStore } from '../stores/auth';
import { ApiError } from '../lib/api';

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

const StandaloneAppsManager = () => {
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType);

  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Upload dialog state
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploadPlatform, setUploadPlatform] = useState<string>('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Delete dialog state
  const [deleteTarget, setDeleteTarget] = useState<TemplateInfo | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadTemplates = async () => {
    if (!token) return;

    setLoading(true);
    setError(null);

    try {
      const response = await listTemplates(token, tokenType || 'Bearer');
      setTemplates(response.templates);
    } catch (err) {
      console.error('Failed to load templates:', err);
      setError(deriveErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, [token]);

  // Upload handlers
  const handleOpenUploadDialog = () => {
    setUploadPlatform('');
    setUploadFile(null);
    setUploadFeedback(null);
    setUploadDialogOpen(true);
  };

  const handleCloseUploadDialog = () => {
    if (!uploading) {
      setUploadDialogOpen(false);
      setUploadPlatform('');
      setUploadFile(null);
      setUploadFeedback(null);
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setUploadFile(selectedFile);
      setUploadFeedback(null);
    }
  };

  const handlePlatformChange = (event: SelectChangeEvent) => {
    setUploadPlatform(event.target.value);
    setUploadFeedback(null);
  };

  const handleUpload = async () => {
    if (!uploadFile || !token || !uploadPlatform) {
      setUploadFeedback({ type: 'error', message: 'Please select a file and platform' });
      return;
    }

    setUploading(true);
    setUploadFeedback(null);

    try {
      await uploadTemplate(uploadPlatform, uploadFile, token, tokenType || 'Bearer');
      setUploadFeedback({ type: 'success', message: 'Template uploaded successfully!' });
      await loadTemplates();

      setTimeout(() => {
        handleCloseUploadDialog();
      }, 1500);
    } catch (err) {
      setUploadFeedback({ type: 'error', message: deriveErrorMessage(err) });
    } finally {
      setUploading(false);
    }
  };

  // Delete handlers
  const handleDeleteClick = (template: TemplateInfo) => {
    setDeleteTarget(template);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget || !token) return;

    setDeleting(true);
    try {
      await deleteTemplate(deleteTarget.platform, token, tokenType || 'Bearer');
      await loadTemplates();
      setDeleteTarget(null);
    } catch (err) {
      console.error('Failed to delete template:', err);
      setError(deriveErrorMessage(err));
    } finally {
      setDeleting(false);
    }
  };

  const handleDownload = (template: TemplateInfo) => {
    window.open(template.download_url, '_blank');
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 3 }}>
        <Button
          variant="contained"
          startIcon={<CloudUploadIcon />}
          onClick={handleOpenUploadDialog}
        >
          Upload Template
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : templates.length === 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Platform</TableCell>
                <TableCell>File Size</TableCell>
                <TableCell>Uploaded</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell colSpan={4} align="center" sx={{ py: 8 }}>
                  <AppsIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary">
                    No templates uploaded
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Upload your first app template to get started
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
                <TableCell>Platform</TableCell>
                <TableCell>File Size</TableCell>
                <TableCell>Uploaded</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {templates.map((template) => (
                <TableRow key={template.platform} hover>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {getPlatformIcon(template.platform)}
                      <Typography>{getPlatformLabel(template.platform)}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell>{formatBytes(template.file_size)}</TableCell>
                  <TableCell>{formatDate(template.uploaded_at)}</TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 0.5 }}>
                      <Tooltip title="Download template">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => handleDownload(template)}
                        >
                          <DownloadIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete template">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteClick(template)}
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

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onClose={handleCloseUploadDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Upload Standalone App Template</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Select a ZIP archive containing the pre-signed standalone app template.
          </Typography>

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Platform</InputLabel>
            <Select
              value={uploadPlatform}
              label="Platform"
              onChange={handlePlatformChange}
              disabled={uploading}
            >
              {STANDALONE_PLATFORMS.map((p) => (
                <MenuItem key={p} value={p}>
                  {PLATFORM_LABELS[p]}
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
            {uploadFile ? uploadFile.name : 'Choose ZIP File'}
            <input
              type="file"
              accept=".zip"
              hidden
              onChange={handleFileChange}
              disabled={uploading}
            />
          </Button>

          {uploading && <LinearProgress sx={{ mb: 2 }} />}

          {uploadFeedback && (
            <Alert severity={uploadFeedback.type} sx={{ mt: 2 }}>
              {uploadFeedback.message}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseUploadDialog} disabled={uploading}>
            Cancel
          </Button>
          <Button
            onClick={handleUpload}
            variant="contained"
            disabled={!uploadFile || !uploadPlatform || uploading}
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onClose={() => !deleting && setDeleteTarget(null)}>
        <DialogTitle>Delete Template?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete the {deleteTarget ? getPlatformLabel(deleteTarget.platform) : ''} template?
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

export default StandaloneAppsManager;
