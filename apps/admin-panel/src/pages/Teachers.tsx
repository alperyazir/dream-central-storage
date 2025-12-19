import { useEffect, useMemo, useState } from 'react';
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
import VisibilityIcon from '@mui/icons-material/Visibility';
import SearchIcon from '@mui/icons-material/Search';
import FilterListIcon from '@mui/icons-material/FilterList';
import ClearIcon from '@mui/icons-material/Clear';
import SchoolIcon from '@mui/icons-material/School';

import {
  TeacherMaterial,
  fetchAllTeacherMaterials,
  listAllTeachers,
  deleteTeacherMaterial,
  downloadTeacherMaterial,
} from '../lib/teachers';
import { useAuthStore } from '../stores/auth';
import TeacherUploadDialog from '../components/TeacherUploadDialog';

import '../styles/page.css';

type SortDirection = 'asc' | 'desc';
type SortField = 'teacher_id' | 'name' | 'content_type' | 'size' | 'last_modified';

const formatDate = (dateString?: string): string => {
  if (!dateString) return '—';
  const date = new Date(dateString);
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

const formatBytes = (bytes?: number): string => {
  if (typeof bytes !== 'number' || bytes === 0) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, exponent);
  return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
};

const getMimeTypeLabel = (contentType: string): string => {
  const mimeMap: Record<string, string> = {
    'application/pdf': 'PDF',
    'audio/mpeg': 'MP3',
    'audio/mp4': 'M4A',
    'audio/wav': 'WAV',
    'audio/ogg': 'OGG',
    'audio/aac': 'AAC',
    'audio/flac': 'FLAC',
    'video/mp4': 'MP4',
    'video/webm': 'WEBM',
    'video/quicktime': 'MOV',
    'image/png': 'PNG',
    'image/jpeg': 'JPEG',
    'image/gif': 'GIF',
    'image/webp': 'WEBP',
    'text/plain': 'TXT',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
  };
  return mimeMap[contentType] || contentType.split('/').pop()?.toUpperCase() || 'FILE';
};

const getMimeTypeColor = (contentType: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
  if (contentType.startsWith('audio/')) return 'info';
  if (contentType.startsWith('video/')) return 'secondary';
  if (contentType.startsWith('image/')) return 'success';
  if (contentType === 'application/pdf') return 'error';
  return 'default';
};

const TeachersPage = () => {
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType);
  const [materials, setMaterials] = useState<TeacherMaterial[]>([]);
  const [teachers, setTeachers] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [teacherFilter, setTeacherFilter] = useState('');
  const [sortField, setSortField] = useState<SortField>('teacher_id');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [deleteTarget, setDeleteTarget] = useState<TeacherMaterial | null>(null);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);

  const loadMaterials = async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const [teacherList, materialsList] = await Promise.all([
        listAllTeachers(token, tokenType || 'Bearer'),
        fetchAllTeacherMaterials(token, tokenType || 'Bearer'),
      ]);
      setTeachers(teacherList);
      setMaterials(materialsList);
    } catch (err) {
      console.error('Failed to fetch teacher materials:', err);
      setError('Failed to load teacher materials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMaterials();
  }, [token]);

  const handleDeleteClick = (material: TeacherMaterial) => {
    setDeleteTarget(material);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget || !token) return;

    try {
      await deleteTeacherMaterial(
        deleteTarget.teacher_id,
        deleteTarget.path,
        token,
        tokenType || 'Bearer'
      );
      await loadMaterials();
      setDeleteTarget(null);
    } catch (err) {
      console.error('Failed to delete material:', err);
      setError('Failed to delete material. Please try again.');
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

  const handleViewMaterial = async (material: TeacherMaterial) => {
    if (!token) return;
    try {
      const blobUrl = await downloadTeacherMaterial(
        material.teacher_id,
        material.path,
        token,
        tokenType || 'Bearer'
      );
      window.open(blobUrl, '_blank');
    } catch (err) {
      console.error('Failed to view material:', err);
      setError('Failed to view material. Please try again.');
    }
  };

  const filteredAndSortedMaterials = useMemo(() => {
    let result = [...materials];

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (material) =>
          material.name.toLowerCase().includes(query) ||
          material.teacher_id.toLowerCase().includes(query) ||
          material.path.toLowerCase().includes(query)
      );
    }

    // Apply teacher filter
    if (teacherFilter) {
      result = result.filter((material) => material.teacher_id === teacherFilter);
    }

    // Apply sorting
    result.sort((a, b) => {
      let aVal: string | number = '';
      let bVal: string | number = '';

      switch (sortField) {
        case 'teacher_id':
          aVal = a.teacher_id;
          bVal = b.teacher_id;
          break;
        case 'name':
          aVal = a.name;
          bVal = b.name;
          break;
        case 'content_type':
          aVal = a.content_type;
          bVal = b.content_type;
          break;
        case 'size':
          aVal = a.size;
          bVal = b.size;
          break;
        case 'last_modified':
          aVal = a.last_modified || '';
          bVal = b.last_modified || '';
          break;
      }

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        const comparison = aVal.localeCompare(bVal, undefined, { sensitivity: 'base' });
        return sortDirection === 'asc' ? comparison : -comparison;
      }

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      return 0;
    });

    return result;
  }, [materials, searchQuery, teacherFilter, sortField, sortDirection]);

  const clearFilters = () => {
    setSearchQuery('');
    setTeacherFilter('');
  };

  const hasActiveFilters = searchQuery || teacherFilter;

  const uniqueTeacherCount = useMemo(() => {
    const uniqueIds = new Set(materials.map((m) => m.teacher_id));
    return uniqueIds.size;
  }, [materials]);

  return (
    <Box component="section" className="page-container">
      <Box className="page-header">
        <Box>
          <Typography variant="h4" component="h1" className="page-title">
            Teachers
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {uniqueTeacherCount} {uniqueTeacherCount === 1 ? 'Teacher' : 'Teachers'} | {materials.length} {materials.length === 1 ? 'Material' : 'Materials'}
          </Typography>
        </Box>
        <Button variant="contained" size="large" onClick={() => setUploadDialogOpen(true)}>
          Upload Material
        </Button>
      </Box>

      {/* Search and Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
            <TextField
              placeholder="Search by filename, teacher ID, or path..."
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

            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel>Teacher</InputLabel>
              <Select
                value={teacherFilter}
                label="Teacher"
                onChange={(e: SelectChangeEvent) => setTeacherFilter(e.target.value)}
              >
                <MenuItem value="">All Teachers</MenuItem>
                {teachers.map((teacher) => (
                  <MenuItem key={teacher} value={teacher}>
                    {teacher}
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

          <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <FilterListIcon fontSize="small" color="action" />
            <Typography variant="body2" color="text.secondary">
              Showing {filteredAndSortedMaterials.length} of {materials.length} materials
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
                <TableCell>
                  <TableSortLabel
                    active={sortField === 'teacher_id'}
                    direction={sortField === 'teacher_id' ? sortDirection : 'asc'}
                    onClick={() => handleSort('teacher_id')}
                  >
                    Teacher ID
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortField === 'name'}
                    direction={sortField === 'name' ? sortDirection : 'asc'}
                    onClick={() => handleSort('name')}
                  >
                    Filename
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortField === 'content_type'}
                    direction={sortField === 'content_type' ? sortDirection : 'asc'}
                    onClick={() => handleSort('content_type')}
                  >
                    Type
                  </TableSortLabel>
                </TableCell>
                <TableCell>
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
                    active={sortField === 'last_modified'}
                    direction={sortField === 'last_modified' ? sortDirection : 'asc'}
                    onClick={() => handleSort('last_modified')}
                  >
                    Upload Date
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredAndSortedMaterials.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 8 }}>
                    <SchoolIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      {hasActiveFilters ? 'No materials match your filters' : 'No materials found'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {hasActiveFilters
                        ? 'Try adjusting your search or filters'
                        : 'Upload your first teacher material to get started'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filteredAndSortedMaterials.map((material) => (
                  <TableRow key={`${material.teacher_id}-${material.path}`} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>
                        {material.teacher_id}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body1">{material.name}</Typography>
                      {material.path !== material.name && (
                        <Typography variant="caption" color="text.secondary">
                          {material.path}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={getMimeTypeLabel(material.content_type)}
                        size="small"
                        color={getMimeTypeColor(material.content_type)}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>{formatBytes(material.size)}</TableCell>
                    <TableCell>{formatDate(material.last_modified)}</TableCell>
                    <TableCell align="right">
                      <Tooltip title="View material">
                        <IconButton size="small" onClick={() => handleViewMaterial(material)}>
                          <VisibilityIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete material">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteClick(material)}
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

      <TeacherUploadDialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        token={token}
        tokenType={tokenType}
        onSuccess={loadMaterials}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Delete Material?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete "{deleteTarget?.name}" from teacher "{deleteTarget?.teacher_id}"?
            This will move it to the trash.
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

export default TeachersPage;
