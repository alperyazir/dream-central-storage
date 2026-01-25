import { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  InputAdornment,
  Paper,
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
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import EditIcon from '@mui/icons-material/Edit';
import SchoolIcon from '@mui/icons-material/School';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import FolderIcon from '@mui/icons-material/Folder';
import StorageIcon from '@mui/icons-material/Storage';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import DescriptionIcon from '@mui/icons-material/Description';
import ImageIcon from '@mui/icons-material/Image';
import AudiotrackIcon from '@mui/icons-material/Audiotrack';
import VideoLibraryIcon from '@mui/icons-material/VideoLibrary';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import SettingsIcon from '@mui/icons-material/Settings';
import DownloadIcon from '@mui/icons-material/Download';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';

import {
  fetchTeacher,
  fetchTeacherStorageStats,
  fetchTeacherMaterials,
  Teacher,
  Material,
  StorageStats,
  formatBytes,
  getAIStatusColor,
  getAIStatusLabel,
} from '../lib/teacherManagement';
import { useAuthStore } from '../stores/auth';
import TeacherFormDialog from '../components/TeacherFormDialog';

import '../styles/page.css';

type SortDirection = 'asc' | 'desc';
type SortField = 'material_name' | 'file_type' | 'size' | 'ai_processing_status' | 'created_at';

const TeacherDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType);

  const [teacher, setTeacher] = useState<Teacher | null>(null);
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [materialsLoading, setMaterialsLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [error, setError] = useState('');
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const loadTeacher = async () => {
    if (!token || !id) return;
    setLoading(true);
    setError('');
    try {
      const data = await fetchTeacher(Number(id), token, tokenType || 'Bearer');
      setTeacher(data);
    } catch (err) {
      console.error('Failed to fetch teacher:', err);
      setError('Failed to load teacher. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const loadStorageStats = async () => {
    if (!token || !id) return;
    setStatsLoading(true);
    try {
      const data = await fetchTeacherStorageStats(Number(id), token, tokenType || 'Bearer');
      setStorageStats(data);
    } catch (err) {
      console.error('Failed to fetch storage stats:', err);
    } finally {
      setStatsLoading(false);
    }
  };

  const loadMaterials = async () => {
    if (!token || !id) return;
    setMaterialsLoading(true);
    try {
      const data = await fetchTeacherMaterials(Number(id), token, tokenType || 'Bearer');
      setMaterials(data);
    } catch (err) {
      console.error('Failed to fetch materials:', err);
    } finally {
      setMaterialsLoading(false);
    }
  };

  useEffect(() => {
    loadTeacher();
    loadStorageStats();
    loadMaterials();
  }, [id, token]);

  const handleFormSuccess = async () => {
    await loadTeacher();
    setFormDialogOpen(false);
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const filteredMaterials = useMemo(() => {
    let filtered = materials;

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (m) =>
          m.material_name.toLowerCase().includes(query) ||
          (m.display_name && m.display_name.toLowerCase().includes(query)) ||
          m.file_type.toLowerCase().includes(query)
      );
    }

    // Sort
    filtered = [...filtered].sort((a, b) => {
      let aVal: string | number = '';
      let bVal: string | number = '';

      switch (sortField) {
        case 'material_name':
          aVal = a.display_name || a.material_name;
          bVal = b.display_name || b.material_name;
          break;
        case 'file_type':
          aVal = a.file_type;
          bVal = b.file_type;
          break;
        case 'size':
          aVal = a.size;
          bVal = b.size;
          break;
        case 'ai_processing_status':
          aVal = a.ai_processing_status;
          bVal = b.ai_processing_status;
          break;
        case 'created_at':
          aVal = new Date(a.created_at).getTime();
          bVal = new Date(b.created_at).getTime();
          break;
      }

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDirection === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return sortDirection === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
    });

    return filtered;
  }, [materials, searchQuery, sortField, sortDirection]);

  const getFileIcon = (fileType: string) => {
    switch (fileType.toLowerCase()) {
      case 'pdf':
        return <PictureAsPdfIcon fontSize="small" color="error" />;
      case 'doc':
      case 'docx':
      case 'txt':
        return <DescriptionIcon fontSize="small" color="primary" />;
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'gif':
      case 'webp':
        return <ImageIcon fontSize="small" color="success" />;
      case 'mp3':
      case 'wav':
      case 'ogg':
        return <AudiotrackIcon fontSize="small" color="secondary" />;
      case 'mp4':
      case 'webm':
      case 'mov':
        return <VideoLibraryIcon fontSize="small" color="warning" />;
      default:
        return <InsertDriveFileIcon fontSize="small" />;
    }
  };

  const getStatusColor = (status: string): 'success' | 'warning' | 'error' | 'default' => {
    switch (status) {
      case 'active':
        return 'success';
      case 'inactive':
        return 'warning';
      case 'suspended':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !teacher) {
    return (
      <Box component="section" className="page-container">
        <Alert severity="error">{error || 'Teacher not found'}</Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/teachers')} sx={{ mt: 2 }}>
          Back to Teachers
        </Button>
      </Box>
    );
  }

  return (
    <Box component="section" className="page-container">
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <IconButton onClick={() => navigate('/teachers')}>
          <ArrowBackIcon />
        </IconButton>
        <SchoolIcon color="primary" sx={{ fontSize: 32 }} />
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h4" component="h1" className="page-title">
            {teacher.display_name || teacher.teacher_id}
          </Typography>
          {teacher.display_name && (
            <Typography variant="body2" color="text.secondary">
              ID: {teacher.teacher_id}
            </Typography>
          )}
        </Box>
        <Button variant="outlined" startIcon={<CloudUploadIcon />} sx={{ mr: 1 }}>
          Upload Material
        </Button>
        <Button variant="contained" startIcon={<EditIcon />} onClick={() => setFormDialogOpen(true)}>
          Edit Teacher
        </Button>
      </Box>

      {/* Teacher Info & Storage Stats Cards */}
      <Box sx={{ display: 'flex', gap: 3, mb: 3, flexDirection: { xs: 'column', md: 'row' } }}>
        {/* Teacher Info Card */}
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Teacher Information
            </Typography>
            <Divider sx={{ mb: 2 }} />
            <Stack spacing={2}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Teacher ID
                </Typography>
                <Typography variant="body1">{teacher.teacher_id}</Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Display Name
                </Typography>
                <Typography variant="body1">{teacher.display_name || '—'}</Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Email
                </Typography>
                <Typography variant="body1">{teacher.email || '—'}</Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Status
                </Typography>
                <Chip
                  label={teacher.status.toUpperCase()}
                  size="small"
                  color={getStatusColor(teacher.status)}
                />
              </Box>
              <Divider />
              <Box>
                <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                  <SettingsIcon fontSize="small" color="action" />
                  <Typography variant="subtitle2" color="text.secondary">
                    AI Settings
                  </Typography>
                </Stack>
                <Stack spacing={1} sx={{ pl: 3 }}>
                  <Typography variant="body2">
                    Auto-process:{' '}
                    <Chip
                      size="small"
                      label={
                        teacher.ai_auto_process_enabled === null
                          ? 'Default'
                          : teacher.ai_auto_process_enabled
                          ? 'Enabled'
                          : 'Disabled'
                      }
                      color={
                        teacher.ai_auto_process_enabled === null
                          ? 'default'
                          : teacher.ai_auto_process_enabled
                          ? 'success'
                          : 'warning'
                      }
                      variant="outlined"
                    />
                  </Typography>
                  <Typography variant="body2">
                    Priority:{' '}
                    {teacher.ai_processing_priority ? (
                      <Chip
                        size="small"
                        label={teacher.ai_processing_priority}
                        variant="outlined"
                        sx={{ textTransform: 'capitalize' }}
                      />
                    ) : (
                      <Chip size="small" label="Default" variant="outlined" />
                    )}
                  </Typography>
                  <Typography variant="body2">
                    Audio Languages:{' '}
                    {teacher.ai_audio_languages ? (
                      <Chip size="small" label={teacher.ai_audio_languages} variant="outlined" />
                    ) : (
                      <Chip size="small" label="Default" variant="outlined" />
                    )}
                  </Typography>
                </Stack>
              </Box>
            </Stack>
          </CardContent>
        </Card>

        {/* Storage Insights Card */}
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
              <StorageIcon color="action" />
              <Typography variant="h6">Storage Insights</Typography>
            </Stack>
            <Divider sx={{ mb: 2 }} />
            {statsLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress size={24} />
              </Box>
            ) : storageStats ? (
              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Total Storage
                  </Typography>
                  <Typography variant="h5" color="primary">
                    {formatBytes(storageStats.total_size)}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Files by Type
                  </Typography>
                  <Stack direction="row" flexWrap="wrap" gap={1}>
                    {Object.entries(storageStats.by_type).map(([type, stats]) => (
                      <Chip
                        key={type}
                        icon={getFileIcon(type)}
                        label={`${type.toUpperCase()}: ${stats.count} (${formatBytes(stats.size)})`}
                        size="small"
                        variant="outlined"
                      />
                    ))}
                    {Object.keys(storageStats.by_type).length === 0 && (
                      <Typography variant="body2" color="text.secondary">
                        No files yet
                      </Typography>
                    )}
                  </Stack>
                </Box>
                <Divider />
                <Box>
                  <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                    <SmartToyIcon fontSize="small" color="action" />
                    <Typography variant="subtitle2" color="text.secondary">
                      AI Processing
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={2}>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Processable
                      </Typography>
                      <Typography variant="h6">{storageStats.ai_processable_count}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Processed
                      </Typography>
                      <Typography variant="h6" color="success.main">
                        {storageStats.ai_processed_count}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Pending
                      </Typography>
                      <Typography variant="h6" color="warning.main">
                        {storageStats.ai_processable_count - storageStats.ai_processed_count}
                      </Typography>
                    </Box>
                  </Stack>
                </Box>
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No storage data available
              </Typography>
            )}
          </CardContent>
        </Card>
      </Box>

      {/* Materials Section */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
            <FolderIcon sx={{ mr: 1, color: 'text.secondary' }} />
            <Typography variant="h6" component="h2">
              Materials
            </Typography>
            <Chip
              label={`${filteredMaterials.length}${searchQuery ? ` / ${materials.length}` : ''}`}
              size="small"
              color="primary"
              variant="outlined"
              sx={{ ml: 1 }}
            />
            <Box sx={{ flexGrow: 1 }} />
            <TextField
              placeholder="Search materials..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              size="small"
              sx={{ width: 250 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
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
            />
          </Box>
          <Divider sx={{ mb: 2 }} />

          {materialsLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : filteredMaterials.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 6 }}>
              <FolderIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                {searchQuery ? 'No materials match your search' : 'No materials yet'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {searchQuery
                  ? 'Try adjusting your search query'
                  : 'Upload materials using the Upload button above.'}
              </Typography>
            </Box>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell width={40}></TableCell>
                    <TableCell>
                      <TableSortLabel
                        active={sortField === 'material_name'}
                        direction={sortField === 'material_name' ? sortDirection : 'asc'}
                        onClick={() => handleSort('material_name')}
                      >
                        Name
                      </TableSortLabel>
                    </TableCell>
                    <TableCell>
                      <TableSortLabel
                        active={sortField === 'file_type'}
                        direction={sortField === 'file_type' ? sortDirection : 'asc'}
                        onClick={() => handleSort('file_type')}
                      >
                        Type
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="right">
                      <TableSortLabel
                        active={sortField === 'size'}
                        direction={sortField === 'size' ? sortDirection : 'asc'}
                        onClick={() => handleSort('size')}
                      >
                        Size
                      </TableSortLabel>
                    </TableCell>
                    <TableCell>
                      <TableSortLabel
                        active={sortField === 'created_at'}
                        direction={sortField === 'created_at' ? sortDirection : 'asc'}
                        onClick={() => handleSort('created_at')}
                      >
                        Uploaded
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="center">
                      <TableSortLabel
                        active={sortField === 'ai_processing_status'}
                        direction={sortField === 'ai_processing_status' ? sortDirection : 'asc'}
                        onClick={() => handleSort('ai_processing_status')}
                      >
                        AI Status
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredMaterials.map((material) => (
                    <TableRow key={material.id} hover>
                      <TableCell>{getFileIcon(material.file_type)}</TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight={500}>
                          {material.display_name || material.material_name}
                        </Typography>
                        {material.display_name && material.display_name !== material.material_name && (
                          <Typography variant="caption" color="text.secondary">
                            {material.material_name}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={material.file_type.toUpperCase()}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell align="right">{formatBytes(material.size)}</TableCell>
                      <TableCell>{formatDate(material.created_at)}</TableCell>
                      <TableCell align="center">
                        <Chip
                          label={getAIStatusLabel(material.ai_processing_status)}
                          size="small"
                          color={getAIStatusColor(material.ai_processing_status)}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                          <Tooltip title="Download">
                            <IconButton size="small">
                              <DownloadIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          {['pdf', 'txt', 'doc', 'docx'].includes(material.file_type.toLowerCase()) &&
                            material.ai_processing_status !== 'completed' &&
                            material.ai_processing_status !== 'processing' &&
                            material.ai_processing_status !== 'queued' && (
                              <Tooltip title="Trigger AI Processing">
                                <IconButton size="small" color="primary">
                                  <PlayArrowIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            )}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Teacher Form Dialog */}
      <TeacherFormDialog
        open={formDialogOpen}
        onClose={() => setFormDialogOpen(false)}
        onSuccess={handleFormSuccess}
        teacher={teacher}
        token={token}
        tokenType={tokenType}
      />
    </Box>
  );
};

export default TeacherDetailPage;
