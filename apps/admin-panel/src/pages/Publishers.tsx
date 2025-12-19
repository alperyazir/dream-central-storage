import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  IconButton,
  InputAdornment,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  SelectChangeEvent,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditIcon from '@mui/icons-material/Edit';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import BusinessIcon from '@mui/icons-material/Business';

import {
  fetchPublishers,
  Publisher,
  deletePublisher,
  fetchPublisherBooks,
  fetchPublisherAssetFiles,
} from '../lib/publishers';
import { useAuthStore } from '../stores/auth';
import PublisherFormDialog from '../components/PublisherFormDialog';
import AuthenticatedImage from '../components/AuthenticatedImage';

import '../styles/page.css';

type SortDirection = 'asc' | 'desc';
type SortField = 'name' | 'display_name' | 'status' | 'created_at';

const PublishersPage = () => {
  const navigate = useNavigate();
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType);
  const [publishers, setPublishers] = useState<Publisher[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sortField, setSortField] = useState<SortField>('name');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [deleteTarget, setDeleteTarget] = useState<Publisher | null>(null);
  const [deleteBookCount, setDeleteBookCount] = useState<number>(0);
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [editingPublisher, setEditingPublisher] = useState<Publisher | null>(null);
  const [bookCounts, setBookCounts] = useState<Record<number, number>>({});
  const [logoFiles, setLogoFiles] = useState<Record<number, string | null>>({});

  const loadPublishers = async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const data = await fetchPublishers(token, tokenType || 'Bearer');
      setPublishers(data);
    } catch (err) {
      console.error('Failed to fetch publishers:', err);
      setError('Failed to load publishers. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPublishers();
  }, [token]);

  // Load book counts and logos for all publishers
  useEffect(() => {
    if (!token || publishers.length === 0) return;

    // Fetch book counts for each publisher
    const loadBookCounts = async () => {
      const counts: Record<number, number> = {};
      await Promise.all(
        publishers.map(async (pub) => {
          try {
            const books = await fetchPublisherBooks(pub.id, token, tokenType || 'Bearer');
            counts[pub.id] = books.length;
          } catch {
            counts[pub.id] = 0;
          }
        })
      );
      setBookCounts(counts);
    };

    // Fetch logo files for each publisher
    const loadLogos = async () => {
      const logos: Record<number, string | null> = {};
      await Promise.all(
        publishers.map(async (pub) => {
          try {
            const files = await fetchPublisherAssetFiles(pub.id, 'logos', token, tokenType || 'Bearer');
            // Get the first logo file if any
            logos[pub.id] = files.length > 0 ? files[0].name : null;
          } catch {
            logos[pub.id] = null;
          }
        })
      );
      setLogoFiles(logos);
    };

    loadBookCounts();
    loadLogos();
  }, [publishers, token, tokenType]);

  const handleDeleteClick = async (publisher: Publisher) => {
    setDeleteTarget(publisher);
    // Fetch book count for this publisher
    if (token) {
      try {
        const books = await fetchPublisherBooks(publisher.id, token, tokenType || 'Bearer');
        setDeleteBookCount(books.length);
      } catch (err) {
        console.error('Failed to fetch publisher books:', err);
        setDeleteBookCount(0);
      }
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget || !token) return;

    try {
      await deletePublisher(deleteTarget.id, token, tokenType || 'Bearer');
      await loadPublishers();
      setDeleteTarget(null);
      setDeleteBookCount(0);
    } catch (err) {
      console.error('Failed to delete publisher:', err);
      setError('Failed to delete publisher. Please try again.');
      setDeleteTarget(null);
      setDeleteBookCount(0);
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const handleViewPublisher = (publisher: Publisher) => {
    navigate(`/publishers/${publisher.id}`);
  };

  const handleEditPublisher = (publisher: Publisher) => {
    setEditingPublisher(publisher);
    setFormDialogOpen(true);
  };

  const handleAddPublisher = () => {
    setEditingPublisher(null);
    setFormDialogOpen(true);
  };

  const handleFormClose = () => {
    setFormDialogOpen(false);
    setEditingPublisher(null);
  };

  const handleFormSuccess = async () => {
    await loadPublishers();
    handleFormClose();
  };

  const statuses = useMemo(() => {
    const set = new Set(publishers.map((p) => p.status));
    return Array.from(set).sort();
  }, [publishers]);

  const filteredAndSortedPublishers = useMemo(() => {
    let result = [...publishers];

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (pub) =>
          pub.name.toLowerCase().includes(query) ||
          (pub.display_name && pub.display_name.toLowerCase().includes(query)) ||
          (pub.description && pub.description.toLowerCase().includes(query))
      );
    }

    // Apply status filter
    if (statusFilter) {
      result = result.filter((pub) => pub.status === statusFilter);
    }

    // Apply sorting
    result.sort((a, b) => {
      let aVal: string | number | null = '';
      let bVal: string | number | null = '';

      switch (sortField) {
        case 'name':
          aVal = a.name;
          bVal = b.name;
          break;
        case 'display_name':
          aVal = a.display_name || a.name;
          bVal = b.display_name || b.name;
          break;
        case 'status':
          aVal = a.status;
          bVal = b.status;
          break;
        case 'created_at':
          aVal = a.created_at;
          bVal = b.created_at;
          break;
      }

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        const comparison = aVal.localeCompare(bVal, undefined, { sensitivity: 'base' });
        return sortDirection === 'asc' ? comparison : -comparison;
      }

      return 0;
    });

    return result;
  }, [publishers, searchQuery, statusFilter, sortField, sortDirection]);

  const clearFilters = () => {
    setSearchQuery('');
    setStatusFilter('');
  };

  const hasActiveFilters = searchQuery || statusFilter;

  const getStatusColor = (
    status: string
  ): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    switch (status) {
      case 'active':
        return 'success';
      case 'inactive':
        return 'default';
      case 'suspended':
        return 'error';
      default:
        return 'default';
    }
  };

  const getLogoUrl = (publisher: Publisher): string | null => {
    const logoFile = logoFiles[publisher.id];
    if (!logoFile) return null;
    return `/api/publishers/${publisher.id}/assets/logos/${encodeURIComponent(logoFile)}`;
  };

  return (
    <Box component="section" className="page-container">
      <Box className="page-header">
        <Box>
          <Typography variant="h4" component="h1" className="page-title">
            Publishers
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage publisher information and view their books
          </Typography>
        </Box>
        <Button variant="contained" size="large" onClick={handleAddPublisher}>
          Add Publisher
        </Button>
      </Box>

      {/* Search and Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
            <TextField
              placeholder="Search by name or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
                endAdornment: searchQuery && (
                  <InputAdornment position="end">
                    <IconButton size="small" onClick={() => setSearchQuery('')}>
                      <ClearIcon fontSize="small" />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
              sx={{ flexGrow: 1, minWidth: 300 }}
            />

            <FormControl sx={{ minWidth: 150 }}>
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                label="Status"
                onChange={(e: SelectChangeEvent) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="">All Statuses</MenuItem>
                {statuses.map((status) => (
                  <MenuItem key={status} value={status}>
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {hasActiveFilters && (
              <Button startIcon={<ClearIcon />} onClick={clearFilters}>
                Clear Filters
              </Button>
            )}
          </Stack>

          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Showing {filteredAndSortedPublishers.length} of {publishers.length} publishers
            </Typography>
          </Box>
        </CardContent>
      </Card>

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
                <TableCell width={64}>Logo</TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortField === 'name'}
                    direction={sortField === 'name' ? sortDirection : 'asc'}
                    onClick={() => handleSort('name')}
                  >
                    Name
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortField === 'display_name'}
                    direction={sortField === 'display_name' ? sortDirection : 'asc'}
                    onClick={() => handleSort('display_name')}
                  >
                    Display Name
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">Books</TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortField === 'status'}
                    direction={sortField === 'status' ? sortDirection : 'asc'}
                    onClick={() => handleSort('status')}
                  >
                    Status
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredAndSortedPublishers.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 8 }}>
                    <BusinessIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      {hasActiveFilters ? 'No publishers match your filters' : 'No publishers found'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {hasActiveFilters
                        ? 'Try adjusting your search or filters'
                        : 'Add your first publisher to get started'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filteredAndSortedPublishers.map((publisher) => (
                  <TableRow
                    key={publisher.id}
                    hover
                    onClick={() => handleViewPublisher(publisher)}
                    sx={{ cursor: 'pointer' }}
                  >
                    <TableCell>
                      <AuthenticatedImage
                        variant="rounded"
                        src={getLogoUrl(publisher) || ''}
                        token={token}
                        tokenType={tokenType || 'Bearer'}
                        sx={{ width: 40, height: 40 }}
                        fallback={<BusinessIcon />}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body1" fontWeight={500}>
                        {publisher.name}
                      </Typography>
                    </TableCell>
                    <TableCell>{publisher.display_name || '—'}</TableCell>
                    <TableCell align="center">
                      <Chip
                        label={bookCounts[publisher.id] ?? '—'}
                        size="small"
                        color={bookCounts[publisher.id] ? 'primary' : 'default'}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={publisher.status.toUpperCase()}
                        size="small"
                        color={getStatusColor(publisher.status)}
                      />
                    </TableCell>
                    <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                      <Tooltip title="Edit publisher">
                        <IconButton size="small" onClick={() => handleEditPublisher(publisher)}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete publisher">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteClick(publisher)}
                        >
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

      {/* Publisher Form Dialog */}
      <PublisherFormDialog
        open={formDialogOpen}
        onClose={handleFormClose}
        onSuccess={handleFormSuccess}
        publisher={editingPublisher}
        token={token}
        tokenType={tokenType}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Delete Publisher?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete "{deleteTarget?.display_name || deleteTarget?.name}"?
            {deleteBookCount > 0 && (
              <>
                <br />
                <br />
                <strong>Warning:</strong> This publisher has {deleteBookCount} book
                {deleteBookCount !== 1 ? 's' : ''} associated with it. Deleting this publisher may
                affect these books.
              </>
            )}
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

export default PublishersPage;
