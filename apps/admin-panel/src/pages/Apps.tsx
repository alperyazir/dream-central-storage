import { useEffect, useState } from 'react';
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
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import AppsIcon from '@mui/icons-material/Apps';

import { SUPPORTED_APP_PLATFORMS, toPlatformSlug } from '../lib/platforms';
import { listAppContents, StorageNode } from '../lib/storage';
import { softDeleteAppBuild } from '../lib/apps';
import { useAuthStore } from '../stores/auth';
import AppUploadDialog from '../components/AppUploadDialog';

import '../styles/page.css';

interface AppBuildRow {
  platform: string;
  platformSlug: string;
  version: string;
  fileName: string;
  storagePath: string;
  size?: number;
}

const collectAppBuildRows = (
  tree: StorageNode,
  platform: string,
  platformSlug: string
): AppBuildRow[] => {
  const rows: AppBuildRow[] = [];

  const traverse = (node: StorageNode, nodePath: string) => {
    const fileName = node.path.split('/').pop() || '';

    if (node.type === 'file' && fileName.endsWith('.ipa')) {
      rows.push({
        platform,
        platformSlug,
        version: '',
        fileName: fileName,
        storagePath: nodePath,
        size: node.size,
      });
    }

    if (node.type === 'folder' && node.children) {
      for (const child of node.children) {
        traverse(child, `${nodePath}/${child.path.split('/').pop() || ''}`);
      }
    }
  };

  traverse(tree, '');
  return rows;
};

const formatBytes = (size?: number) => {
  if (typeof size !== 'number') return '—';
  if (size === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB'];
  const exponent = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1);
  const value = size / Math.pow(1024, exponent);
  return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
};

const AppsPage = () => {
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType);
  const [appBuilds, setAppBuilds] = useState<AppBuildRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<AppBuildRow | null>(null);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);

  const loadApps = async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const appResponses = await Promise.all(
        SUPPORTED_APP_PLATFORMS.map((platform) =>
          listAppContents(toPlatformSlug(platform), token, tokenType || 'Bearer')
        )
      );

      const appRows = appResponses.flatMap((tree, index) =>
        collectAppBuildRows(tree, SUPPORTED_APP_PLATFORMS[index], toPlatformSlug(SUPPORTED_APP_PLATFORMS[index]))
      );

      setAppBuilds(appRows);
    } catch (err) {
      console.error('Failed to fetch apps:', err);
      setError('Failed to load applications. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApps();
  }, [token]);

  const handleDeleteClick = (app: AppBuildRow) => {
    setDeleteTarget(app);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget || !token) return;

    try {
      await softDeleteAppBuild(
        deleteTarget.platformSlug,
        deleteTarget.storagePath,
        token,
        tokenType || 'Bearer'
      );
      await loadApps();
      setDeleteTarget(null);
    } catch (err) {
      console.error('Failed to delete app build:', err);
      setError('Failed to delete app build. Please try again.');
    }
  };

  return (
    <Box component="section" className="page-container">
      <Box className="page-header">
        <Box>
          <Typography variant="h4" component="h1" className="page-title">
            Applications
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Currently tracking {appBuilds.length} build artifacts across {SUPPORTED_APP_PLATFORMS.length} platforms
          </Typography>
        </Box>
        <Button variant="contained" size="large" onClick={() => setUploadDialogOpen(true)}>
          Upload App
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Platform</TableCell>
                <TableCell>Version</TableCell>
                <TableCell>File</TableCell>
                <TableCell>Size</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {appBuilds.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ py: 8 }}>
                    <AppsIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      No application builds found
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Upload your first app build to get started
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                appBuilds.map((app, index) => (
                  <TableRow key={index} hover>
                    <TableCell>{app.platform}</TableCell>
                    <TableCell>{app.version || '—'}</TableCell>
                    <TableCell>{app.fileName}</TableCell>
                    <TableCell>{formatBytes(app.size)}</TableCell>
                    <TableCell align="right">
                      <Tooltip title="Delete build">
                        <IconButton size="small" color="error" onClick={() => handleDeleteClick(app)}>
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <AppUploadDialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        platforms={SUPPORTED_APP_PLATFORMS}
        token={token}
        tokenType={tokenType}
        onSuccess={loadApps}
      />

      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Delete App Build?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete "{deleteTarget?.fileName}"? This will move it to the trash.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AppsPage;
