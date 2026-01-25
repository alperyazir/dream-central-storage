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
  Tabs,
  Tab,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import RestoreIcon from '@mui/icons-material/Restore';
import EditIcon from '@mui/icons-material/Edit';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import SchoolIcon from '@mui/icons-material/School';
import StorageIcon from '@mui/icons-material/Storage';
import FolderIcon from '@mui/icons-material/Folder';

import {
  fetchTeachers,
  fetchTrashedTeachers,
  TeacherListItem,
  deleteTeacher,
  restoreTeacher,
  permanentDeleteTeacher,
  formatBytes,
} from '../lib/teacherManagement';
import { useAuthStore } from '../stores/auth';
import TeacherFormDialog from '../components/TeacherFormDialog';

import '../styles/page.css';

type SortDirection = 'asc' | 'desc';
type SortField = 'teacher_id' | 'display_name' | 'material_count' | 'total_storage_size' | 'status' | 'created_at';

const TeachersManagementPage = () => {
  const navigate = useNavigate();
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType);
  const [teachers, setTeachers] = useState<TeacherListItem[]>([]);
  const [trashedTeachers, setTrashedTeachers] = useState<TeacherListItem[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('teacher_id');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [deleteTarget, setDeleteTarget] = useState<TeacherListItem | null>(null);
  const [permanentDeleteTarget, setPermanentDeleteTarget] = useState<TeacherListItem | null>(null);
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [editingTeacher, setEditingTeacher] = useState<TeacherListItem | null>(null);

  const loadTeachers = async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const [activeData, trashedData] = await Promise.all([
        fetchTeachers(token, tokenType || 'Bearer'),
        fetchTrashedTeachers(token, tokenType || 'Bearer'),
      ]);
      setTeachers(activeData);
      setTrashedTeachers(trashedData);
    } catch (err) {
      console.error('Failed to fetch teachers:', err);
      setError('Failed to load teachers. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTeachers();
  }, [token]);

  const handleDeleteClick = (teacher: TeacherListItem) => {
    setDeleteTarget(teacher);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget || !token) return;
    try {
      await deleteTeacher(deleteTarget.id, token, tokenType || 'Bearer');
      await loadTeachers();
      setDeleteTarget(null);
    } catch (err) {
      console.error('Failed to delete teacher:', err);
      setError('Failed to delete teacher. Please try again.');
      setDeleteTarget(null);
    }
  };

  const handleRestore = async (teacher: TeacherListItem) => {
    if (!token) return;
    try {
      await restoreTeacher(teacher.id, token, tokenType || 'Bearer');
      await loadTeachers();
    } catch (err) {
      console.error('Failed to restore teacher:', err);
      setError('Failed to restore teacher. Please try again.');
    }
  };

  const handlePermanentDeleteClick = (teacher: TeacherListItem) => {
    setPermanentDeleteTarget(teacher);
  };

  const handlePermanentDeleteConfirm = async () => {
    if (!permanentDeleteTarget || !token) return;
    try {
      await permanentDeleteTeacher(permanentDeleteTarget.id, token, tokenType || 'Bearer');
      await loadTeachers();
      setPermanentDeleteTarget(null);
    } catch (err) {
      console.error('Failed to permanently delete teacher:', err);
      setError('Failed to permanently delete teacher. Please try again.');
      setPermanentDeleteTarget(null);
    }
  };

  const handleEditClick = (teacher: TeacherListItem) => {
    setEditingTeacher(teacher);
    setFormDialogOpen(true);
  };

  const handleAddClick = () => {
    setEditingTeacher(null);
    setFormDialogOpen(true);
  };

  const handleFormClose = () => {
    setFormDialogOpen(false);
    setEditingTeacher(null);
  };

  const handleFormSuccess = () => {
    setFormDialogOpen(false);
    setEditingTeacher(null);
    loadTeachers();
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const handleRowClick = (teacher: TeacherListItem) => {
    navigate(`/teachers/${teacher.id}`);
  };

  const currentTeachers = activeTab === 0 ? teachers : trashedTeachers;

  const filteredTeachers = useMemo(() => {
    let filtered = currentTeachers;

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (t) =>
          t.teacher_id.toLowerCase().includes(query) ||
          (t.display_name && t.display_name.toLowerCase().includes(query)) ||
          (t.email && t.email.toLowerCase().includes(query))
      );
    }

    // Sort
    filtered = [...filtered].sort((a, b) => {
      let aVal: string | number = '';
      let bVal: string | number = '';

      switch (sortField) {
        case 'teacher_id':
          aVal = a.teacher_id;
          bVal = b.teacher_id;
          break;
        case 'display_name':
          aVal = a.display_name || '';
          bVal = b.display_name || '';
          break;
        case 'material_count':
          aVal = a.material_count;
          bVal = b.material_count;
          break;
        case 'total_storage_size':
          aVal = a.total_storage_size;
          bVal = b.total_storage_size;
          break;
        case 'status':
          aVal = a.status;
          bVal = b.status;
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
  }, [currentTeachers, searchQuery, sortField, sortDirection]);

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

  if (loading) {
    return (
      <Box className="page-container" display="flex" alignItems="center" justifyContent="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box className="page-container">
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
        <Stack direction="row" alignItems="center" spacing={2}>
          <SchoolIcon color="primary" sx={{ fontSize: 32 }} />
          <Typography variant="h4" component="h1">
            Teachers Management
          </Typography>
        </Stack>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleAddClick}>
          Add Teacher
        </Button>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <Tabs value={activeTab} onChange={(_, val) => setActiveTab(val)} sx={{ mb: 2 }}>
        <Tab label={`Active (${teachers.length})`} />
        <Tab label={`Trash (${trashedTeachers.length})`} />
      </Tabs>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={2} alignItems="center">
            <TextField
              placeholder="Search by ID, name, or email..."
              size="small"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              sx={{ minWidth: 300 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon color="action" />
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
            <Box flexGrow={1} />
            <Typography variant="body2" color="text.secondary">
              {filteredTeachers.length} teacher{filteredTeachers.length !== 1 ? 's' : ''}
            </Typography>
          </Stack>
        </CardContent>
      </Card>

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
                  active={sortField === 'display_name'}
                  direction={sortField === 'display_name' ? sortDirection : 'asc'}
                  onClick={() => handleSort('display_name')}
                >
                  Display Name
                </TableSortLabel>
              </TableCell>
              <TableCell>Email</TableCell>
              <TableCell align="center">
                <TableSortLabel
                  active={sortField === 'material_count'}
                  direction={sortField === 'material_count' ? sortDirection : 'asc'}
                  onClick={() => handleSort('material_count')}
                >
                  Materials
                </TableSortLabel>
              </TableCell>
              <TableCell align="right">
                <TableSortLabel
                  active={sortField === 'total_storage_size'}
                  direction={sortField === 'total_storage_size' ? sortDirection : 'asc'}
                  onClick={() => handleSort('total_storage_size')}
                >
                  Storage
                </TableSortLabel>
              </TableCell>
              <TableCell align="center">
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
            {filteredTeachers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">
                    {searchQuery ? 'No teachers match your search' : 'No teachers found'}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              filteredTeachers.map((teacher) => (
                <TableRow
                  key={teacher.id}
                  hover
                  onClick={() => handleRowClick(teacher)}
                  sx={{ cursor: 'pointer' }}
                >
                  <TableCell>
                    <Stack direction="row" alignItems="center" spacing={1}>
                      <SchoolIcon fontSize="small" color="action" />
                      <Typography variant="body2" fontWeight={500}>
                        {teacher.teacher_id}
                      </Typography>
                    </Stack>
                  </TableCell>
                  <TableCell>{teacher.display_name || '—'}</TableCell>
                  <TableCell>{teacher.email || '—'}</TableCell>
                  <TableCell align="center">
                    <Chip
                      icon={<FolderIcon />}
                      label={teacher.material_count}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Stack direction="row" alignItems="center" justifyContent="flex-end" spacing={0.5}>
                      <StorageIcon fontSize="small" color="action" />
                      <Typography variant="body2">{formatBytes(teacher.total_storage_size)}</Typography>
                    </Stack>
                  </TableCell>
                  <TableCell align="center">
                    <Chip label={teacher.status} size="small" color={getStatusColor(teacher.status)} />
                  </TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                      {activeTab === 0 ? (
                        <>
                          <Tooltip title="Edit">
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleEditClick(teacher);
                              }}
                            >
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Move to Trash">
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteClick(teacher);
                              }}
                            >
                              <DeleteOutlineIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </>
                      ) : (
                        <>
                          <Tooltip title="Restore">
                            <IconButton
                              size="small"
                              color="primary"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRestore(teacher);
                              }}
                            >
                              <RestoreIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Delete Permanently">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={(e) => {
                                e.stopPropagation();
                                handlePermanentDeleteClick(teacher);
                              }}
                            >
                              <DeleteForeverIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </>
                      )}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Move to Trash?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to move teacher "{deleteTarget?.display_name || deleteTarget?.teacher_id}" to
            trash?
            {deleteTarget && deleteTarget.material_count > 0 && (
              <Box component="span" sx={{ display: 'block', mt: 1, color: 'warning.main' }}>
                This teacher has {deleteTarget.material_count} material(s).
              </Box>
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error">
            Move to Trash
          </Button>
        </DialogActions>
      </Dialog>

      {/* Permanent Delete Confirmation Dialog */}
      <Dialog open={!!permanentDeleteTarget} onClose={() => setPermanentDeleteTarget(null)}>
        <DialogTitle>Permanently Delete?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to permanently delete teacher "
            {permanentDeleteTarget?.display_name || permanentDeleteTarget?.teacher_id}"?
            <Box component="span" sx={{ display: 'block', mt: 1, color: 'error.main', fontWeight: 500 }}>
              This action cannot be undone. All materials and AI data will be deleted.
            </Box>
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPermanentDeleteTarget(null)}>Cancel</Button>
          <Button onClick={handlePermanentDeleteConfirm} color="error" variant="contained">
            Delete Permanently
          </Button>
        </DialogActions>
      </Dialog>

      {/* Teacher Form Dialog */}
      <TeacherFormDialog
        open={formDialogOpen}
        onClose={handleFormClose}
        onSuccess={handleFormSuccess}
        teacher={editingTeacher}
        token={token}
        tokenType={tokenType}
      />
    </Box>
  );
};

export default TeachersManagementPage;
