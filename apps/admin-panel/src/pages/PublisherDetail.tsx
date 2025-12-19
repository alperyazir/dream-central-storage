import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMemo } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Divider,
  IconButton,
  InputAdornment,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Popover,
  Stack,
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
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import EditIcon from '@mui/icons-material/Edit';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import FolderIcon from '@mui/icons-material/Folder';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import ImageIcon from '@mui/icons-material/Image';
import BusinessIcon from '@mui/icons-material/Business';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';

import {
  fetchPublisher,
  fetchPublisherBooks,
  fetchPublisherAssets,
  fetchPublisherAssetFiles,
  Publisher,
  PublisherBook,
  AssetTypeInfo,
  AssetFileInfo,
} from '../lib/publishers';
import { useAuthStore } from '../stores/auth';
import PublisherFormDialog from '../components/PublisherFormDialog';
import PublisherUploadDialog from '../components/PublisherUploadDialog';
import AuthenticatedImage from '../components/AuthenticatedImage';

import '../styles/page.css';

const PublisherDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType);

  const [publisher, setPublisher] = useState<Publisher | null>(null);
  const [books, setBooks] = useState<PublisherBook[]>([]);
  const [assets, setAssets] = useState<AssetTypeInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [booksLoading, setBooksLoading] = useState(true);
  const [assetsLoading, setAssetsLoading] = useState(true);
  const [error, setError] = useState('');
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [activityAnchorEl, setActivityAnchorEl] = useState<HTMLElement | null>(null);
  const [selectedBookActivities, setSelectedBookActivities] = useState<Record<string, number> | null>(null);
  const [expandedAssets, setExpandedAssets] = useState<Set<string>>(new Set());
  const [assetFiles, setAssetFiles] = useState<Record<string, AssetFileInfo[]>>({});
  const [bookSearch, setBookSearch] = useState('');
  const [assetSearch, setAssetSearch] = useState('');

  // Filtered books based on search query
  const filteredBooks = useMemo(() => {
    if (!bookSearch.trim()) return books;
    const query = bookSearch.toLowerCase().trim();
    return books.filter(
      (book) =>
        book.book_name.toLowerCase().includes(query) ||
        (book.book_title && book.book_title.toLowerCase().includes(query)) ||
        (book.category && book.category.toLowerCase().includes(query)) ||
        book.language.toLowerCase().includes(query)
    );
  }, [books, bookSearch]);

  // Filtered assets based on search query
  const filteredAssets = useMemo(() => {
    if (!assetSearch.trim()) return assets;
    const query = assetSearch.toLowerCase().trim();
    return assets.filter((asset) => asset.name.toLowerCase().includes(query));
  }, [assets, assetSearch]);

  const loadPublisher = async () => {
    if (!token || !id) return;
    setLoading(true);
    setError('');
    try {
      const data = await fetchPublisher(Number(id), token, tokenType || 'Bearer');
      setPublisher(data);
    } catch (err) {
      console.error('Failed to fetch publisher:', err);
      setError('Failed to load publisher. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const loadBooks = async () => {
    if (!token || !id) return;
    setBooksLoading(true);
    try {
      const data = await fetchPublisherBooks(Number(id), token, tokenType || 'Bearer');
      setBooks(data);
    } catch (err) {
      console.error('Failed to fetch publisher books:', err);
    } finally {
      setBooksLoading(false);
    }
  };

  const loadAssets = async () => {
    if (!token || !id) return;
    setAssetsLoading(true);
    try {
      const data = await fetchPublisherAssets(Number(id), token, tokenType || 'Bearer');
      setAssets(data.asset_types);
    } catch (err) {
      console.error('Failed to fetch publisher assets:', err);
    } finally {
      setAssetsLoading(false);
    }
  };

  useEffect(() => {
    loadPublisher();
    loadBooks();
    loadAssets();
  }, [id, token]);

  const handleFormSuccess = async () => {
    await loadPublisher();
    setFormDialogOpen(false);
  };

  const handleUploadSuccess = async () => {
    await loadBooks();
    await loadAssets();
  };

  const getBookCoverUrl = (bookName: string): string => {
    return `/api/storage/books/${encodeURIComponent(publisher?.name || '')}/${encodeURIComponent(bookName)}/object?path=${encodeURIComponent('images/book_cover.png')}`;
  };

  const handleActivityClick = (event: React.MouseEvent<HTMLElement>, activities: Record<string, number> | undefined) => {
    if (activities && Object.keys(activities).length > 0) {
      setActivityAnchorEl(event.currentTarget);
      setSelectedBookActivities(activities);
    }
  };

  const handleActivityClose = () => {
    setActivityAnchorEl(null);
    setSelectedBookActivities(null);
  };

  const handleAssetExpand = async (assetType: string) => {
    const newExpanded = new Set(expandedAssets);
    if (newExpanded.has(assetType)) {
      newExpanded.delete(assetType);
    } else {
      newExpanded.add(assetType);
      // Load files if not already loaded
      if (!assetFiles[assetType] && token && id) {
        try {
          const files = await fetchPublisherAssetFiles(Number(id), assetType, token, tokenType || 'Bearer');
          setAssetFiles((prev) => ({ ...prev, [assetType]: files }));
        } catch (err) {
          console.error('Failed to fetch asset files:', err);
        }
      }
    }
    setExpandedAssets(newExpanded);
  };

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext || '')) {
      return <ImageIcon fontSize="small" />;
    }
    return <InsertDriveFileIcon fontSize="small" />;
  };

  const getAssetFileUrl = (assetType: string, filename: string): string => {
    return `/api/publishers/${id}/assets/${encodeURIComponent(assetType)}/${encodeURIComponent(filename)}`;
  };

  const getPublisherLogoUrl = (): string | null => {
    const logoAsset = assets.find((a) => a.name === 'logos');
    if (!logoAsset || logoAsset.file_count === 0) return null;
    const logoFiles = assetFiles['logos'];
    if (logoFiles && logoFiles.length > 0) {
      return getAssetFileUrl('logos', logoFiles[0].name);
    }
    return null;
  };

  // Load logo files on mount for header display
  useEffect(() => {
    const loadLogoFiles = async () => {
      if (!token || !id) return;
      const logoAsset = assets.find((a) => a.name === 'logos');
      if (logoAsset && logoAsset.file_count > 0 && !assetFiles['logos']) {
        try {
          const files = await fetchPublisherAssetFiles(Number(id), 'logos', token, tokenType || 'Bearer');
          setAssetFiles((prev) => ({ ...prev, logos: files }));
        } catch (err) {
          console.error('Failed to fetch logo files:', err);
        }
      }
    };
    loadLogoFiles();
  }, [assets, token, id, tokenType]);

  const formatBytes = (bytes?: number): string => {
    if (typeof bytes !== 'number' || bytes === 0) return '—';
    const units = ['B', 'KB', 'MB', 'GB'];
    const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const value = bytes / Math.pow(1024, exponent);
    return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
  };

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

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !publisher) {
    return (
      <Box component="section" className="page-container">
        <Alert severity="error">{error || 'Publisher not found'}</Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/publishers')} sx={{ mt: 2 }}>
          Back to Publishers
        </Button>
      </Box>
    );
  }

  return (
    <Box component="section" className="page-container">
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <IconButton onClick={() => navigate('/publishers')}>
          <ArrowBackIcon />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h4" component="h1" className="page-title">
            {publisher.display_name || publisher.name}
          </Typography>
          {publisher.display_name && (
            <Typography variant="body2" color="text.secondary">
              ID: {publisher.name}
            </Typography>
          )}
        </Box>
        <Button
          variant="contained"
          startIcon={<EditIcon />}
          onClick={() => setFormDialogOpen(true)}
        >
          Edit Publisher
        </Button>
      </Box>

      {/* Publisher Info Card */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
            {/* Publisher Logo */}
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <AuthenticatedImage
                variant="rounded"
                src={getPublisherLogoUrl() || ''}
                token={token}
                tokenType={tokenType || 'Bearer'}
                sx={{ width: 120, height: 120, bgcolor: 'action.hover' }}
                imgProps={{ style: { objectFit: 'contain', padding: 8 } }}
                fallback={<BusinessIcon sx={{ fontSize: 64 }} />}
              />
            </Box>
            <Box sx={{ flex: 1 }}>
              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Name
                  </Typography>
                  <Typography variant="body1">{publisher.name}</Typography>
                </Box>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Display Name
                  </Typography>
                  <Typography variant="body1">{publisher.display_name || '—'}</Typography>
                </Box>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Status
                  </Typography>
                  <Chip
                    label={publisher.status.toUpperCase()}
                    size="small"
                    color={getStatusColor(publisher.status)}
                  />
                </Box>
              </Stack>
            </Box>
            <Box sx={{ flex: 1 }}>
              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Contact Email
                  </Typography>
                  <Typography variant="body1">{publisher.contact_email || '—'}</Typography>
                </Box>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Description
                  </Typography>
                  <Typography variant="body1">{publisher.description || '—'}</Typography>
                </Box>
              </Stack>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Books Section */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
            <MenuBookIcon sx={{ mr: 1, color: 'text.secondary' }} />
            <Typography variant="h6" component="h2">
              Books
            </Typography>
            <Chip
              label={`${filteredBooks.length}${bookSearch ? ` / ${books.length}` : ''}`}
              size="small"
              color="primary"
              variant="outlined"
              sx={{ ml: 1 }}
            />
            <Box sx={{ flexGrow: 1 }} />
            <TextField
              placeholder="Search books..."
              value={bookSearch}
              onChange={(e) => setBookSearch(e.target.value)}
              size="small"
              sx={{ width: 220 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
                endAdornment: bookSearch && (
                  <InputAdornment position="end">
                    <IconButton size="small" onClick={() => setBookSearch('')}>
                      <ClearIcon fontSize="small" />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <Button
              variant="contained"
              startIcon={<CloudUploadIcon />}
              onClick={() => setUploadDialogOpen(true)}
              size="small"
            >
              Upload
            </Button>
          </Box>
          <Divider sx={{ mb: 2 }} />
          {booksLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : filteredBooks.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 6 }}>
              <MenuBookIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                {bookSearch ? 'No books match your search' : 'No books yet'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {bookSearch
                  ? 'Try adjusting your search query'
                  : "This publisher doesn't have any books yet."}
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell width={80}>Cover</TableCell>
                    <TableCell>Title</TableCell>
                    <TableCell>Language</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell>Activities</TableCell>
                    <TableCell>Size</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredBooks.map((book) => (
                    <TableRow key={book.id} hover>
                      <TableCell>
                        <AuthenticatedImage
                          variant="rounded"
                          src={getBookCoverUrl(book.book_name)}
                          token={token}
                          tokenType={tokenType || 'Bearer'}
                          sx={{ width: 48, height: 48 }}
                          fallback={<MenuBookIcon />}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body1" fontWeight={500}>
                          {book.book_title || book.book_name}
                        </Typography>
                        {book.book_title !== book.book_name && (
                          <Typography variant="caption" color="text.secondary">
                            {book.book_name}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip label={book.language.toUpperCase()} size="small" />
                      </TableCell>
                      <TableCell>{book.category || '—'}</TableCell>
                      <TableCell>
                        <Tooltip title={book.activity_details ? 'Click to see activity breakdown' : ''}>
                          <Chip
                            label={book.activity_count || 0}
                            size="small"
                            color={book.activity_count ? 'primary' : 'default'}
                            variant="outlined"
                            onClick={(e) => handleActivityClick(e, book.activity_details)}
                            sx={{ cursor: book.activity_details ? 'pointer' : 'default' }}
                          />
                        </Tooltip>
                      </TableCell>
                      <TableCell>{formatBytes(book.total_size)}</TableCell>
                      <TableCell>
                        <Chip label={book.status} size="small" variant="outlined" />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Assets Section */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
            <FolderIcon sx={{ mr: 1, color: 'text.secondary' }} />
            <Typography variant="h6" component="h2">
              Assets
            </Typography>
            <Chip
              label={`${filteredAssets.length}${assetSearch ? ` / ${assets.length}` : ''}`}
              size="small"
              color="primary"
              variant="outlined"
              sx={{ ml: 1 }}
            />
            <Box sx={{ flexGrow: 1 }} />
            <TextField
              placeholder="Search assets..."
              value={assetSearch}
              onChange={(e) => setAssetSearch(e.target.value)}
              size="small"
              sx={{ width: 220 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
                endAdornment: assetSearch && (
                  <InputAdornment position="end">
                    <IconButton size="small" onClick={() => setAssetSearch('')}>
                      <ClearIcon fontSize="small" />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
          </Box>
          <Divider sx={{ mb: 2 }} />
          {assetsLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : filteredAssets.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 6 }}>
              <FolderIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                {assetSearch ? 'No assets match your search' : 'No assets yet'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {assetSearch
                  ? 'Try adjusting your search query'
                  : 'Upload logos, materials, or other assets using the Upload button above.'}
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell width={40}></TableCell>
                    <TableCell>Asset Type</TableCell>
                    <TableCell align="right">Files</TableCell>
                    <TableCell align="right">Total Size</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredAssets.map((asset) => (
                    <>
                      <TableRow
                        key={asset.name}
                        hover
                        onClick={() => handleAssetExpand(asset.name)}
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell>
                          <IconButton size="small">
                            {expandedAssets.has(asset.name) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                          </IconButton>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <FolderIcon fontSize="small" color="action" />
                            <Typography variant="body1" sx={{ textTransform: 'capitalize' }}>
                              {asset.name}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={asset.file_count}
                            size="small"
                            color={asset.file_count ? 'primary' : 'default'}
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="right">{formatBytes(asset.total_size)}</TableCell>
                      </TableRow>
                      <TableRow key={`${asset.name}-files`}>
                        <TableCell colSpan={4} sx={{ p: 0, borderBottom: expandedAssets.has(asset.name) ? undefined : 'none' }}>
                          <Collapse in={expandedAssets.has(asset.name)} timeout="auto" unmountOnExit>
                            <Box sx={{ py: 1, px: 2, bgcolor: 'action.hover' }}>
                              {assetFiles[asset.name] ? (
                                <List dense disablePadding>
                                  {assetFiles[asset.name].map((file) => {
                                    const isImage = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(
                                      file.name.split('.').pop()?.toLowerCase() || ''
                                    );
                                    return (
                                      <ListItem
                                        key={file.name}
                                        sx={{ pl: 6 }}
                                        secondaryAction={
                                          <Typography variant="caption" color="text.secondary">
                                            {formatBytes(file.size)}
                                          </Typography>
                                        }
                                      >
                                        <ListItemIcon sx={{ minWidth: 56 }}>
                                          {isImage ? (
                                            <AuthenticatedImage
                                              variant="rounded"
                                              src={getAssetFileUrl(asset.name, file.name)}
                                              token={token}
                                              tokenType={tokenType || 'Bearer'}
                                              sx={{ width: 40, height: 40 }}
                                              fallback={<ImageIcon />}
                                            />
                                          ) : (
                                            getFileIcon(file.name)
                                          )}
                                        </ListItemIcon>
                                        <ListItemText
                                          primary={file.name}
                                          primaryTypographyProps={{ variant: 'body2' }}
                                        />
                                      </ListItem>
                                    );
                                  })}
                                </List>
                              ) : (
                                <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                                  <CircularProgress size={20} />
                                </Box>
                              )}
                            </Box>
                          </Collapse>
                        </TableCell>
                      </TableRow>
                    </>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Publisher Form Dialog */}
      <PublisherFormDialog
        open={formDialogOpen}
        onClose={() => setFormDialogOpen(false)}
        onSuccess={handleFormSuccess}
        publisher={publisher}
        token={token}
        tokenType={tokenType}
      />

      {/* Publisher Upload Dialog */}
      <PublisherUploadDialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        onSuccess={handleUploadSuccess}
        token={token}
        tokenType={tokenType}
        initialPublisherId={publisher?.id}
      />

      {/* Activity Details Popover */}
      <Popover
        open={Boolean(activityAnchorEl)}
        anchorEl={activityAnchorEl}
        onClose={handleActivityClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'center',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'center',
        }}
      >
        <Box sx={{ p: 2, minWidth: 200 }}>
          <Typography variant="subtitle2" gutterBottom>
            Activity Breakdown
          </Typography>
          <Divider sx={{ mb: 1 }} />
          {selectedBookActivities && (
            <List dense disablePadding>
              {Object.entries(selectedBookActivities).map(([type, count]) => (
                <ListItem key={type} disablePadding sx={{ py: 0.5 }}>
                  <ListItemText
                    primary={type}
                    primaryTypographyProps={{ variant: 'body2', sx: { textTransform: 'capitalize' } }}
                  />
                  <Chip label={count} size="small" variant="outlined" />
                </ListItem>
              ))}
            </List>
          )}
        </Box>
      </Popover>
    </Box>
  );
};

export default PublisherDetailPage;
