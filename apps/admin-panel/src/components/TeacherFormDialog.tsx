import { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  SelectChangeEvent,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import SettingsIcon from '@mui/icons-material/Settings';

import {
  createTeacher,
  updateTeacher,
  TeacherCreate,
  TeacherUpdate,
  TeacherListItem,
  Teacher,
} from '../lib/teacherManagement';

interface TeacherFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  teacher?: TeacherListItem | Teacher | null;
  token: string | null;
  tokenType: string | null;
}

const TeacherFormDialog = ({
  open,
  onClose,
  onSuccess,
  teacher,
  token,
  tokenType,
}: TeacherFormDialogProps) => {
  const isEdit = !!teacher;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showAISettings, setShowAISettings] = useState(false);

  // Form fields
  const [teacherId, setTeacherId] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState('active');
  const [aiAutoProcessEnabled, setAiAutoProcessEnabled] = useState<boolean | null>(null);
  const [aiProcessingPriority, setAiProcessingPriority] = useState<string>('');
  const [aiAudioLanguages, setAiAudioLanguages] = useState('');

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      if (teacher) {
        setTeacherId(teacher.teacher_id);
        setDisplayName(teacher.display_name || '');
        setEmail(teacher.email || '');
        setStatus(teacher.status || 'active');
        setAiAutoProcessEnabled(teacher.ai_auto_process_enabled);
        setAiProcessingPriority(teacher.ai_processing_priority || '');
        setAiAudioLanguages(teacher.ai_audio_languages || '');
        setShowAISettings(
          teacher.ai_auto_process_enabled !== null ||
          teacher.ai_processing_priority !== null ||
          teacher.ai_audio_languages !== null
        );
      } else {
        setTeacherId('');
        setDisplayName('');
        setEmail('');
        setStatus('active');
        setAiAutoProcessEnabled(null);
        setAiProcessingPriority('');
        setAiAudioLanguages('');
        setShowAISettings(false);
      }
      setError('');
    }
  }, [open, teacher]);

  const handleSubmit = async () => {
    if (!token) return;

    // Validation
    if (!teacherId.trim()) {
      setError('Teacher ID is required');
      return;
    }

    if (email && !email.includes('@')) {
      setError('Please enter a valid email address');
      return;
    }

    setLoading(true);
    setError('');

    try {
      if (isEdit && teacher) {
        // Update existing teacher
        const updateData: TeacherUpdate = {
          display_name: displayName || undefined,
          email: email || undefined,
          status: status,
          ai_auto_process_enabled: aiAutoProcessEnabled,
          ai_processing_priority: aiProcessingPriority || null,
          ai_audio_languages: aiAudioLanguages || null,
        };
        await updateTeacher(teacher.id, updateData, token, tokenType || 'Bearer');
      } else {
        // Create new teacher
        const createData: TeacherCreate = {
          teacher_id: teacherId.trim(),
          display_name: displayName || undefined,
          email: email || undefined,
          ai_auto_process_enabled: aiAutoProcessEnabled,
          ai_processing_priority: aiProcessingPriority || undefined,
          ai_audio_languages: aiAudioLanguages || undefined,
        };
        await createTeacher(createData, token, tokenType || 'Bearer');
      }
      onSuccess();
    } catch (err: unknown) {
      console.error('Failed to save teacher:', err);
      if (err && typeof err === 'object' && 'body' in err) {
        const apiError = err as { body?: { detail?: string } };
        setError(apiError.body?.detail || 'Failed to save teacher. Please try again.');
      } else {
        setError('Failed to save teacher. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAIAutoProcessChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setAiAutoProcessEnabled(event.target.checked);
  };

  const handleAIAutoProcessReset = () => {
    setAiAutoProcessEnabled(null);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? 'Edit Teacher' : 'Add New Teacher'}</DialogTitle>
      <DialogContent>
        <Stack spacing={3} sx={{ mt: 1 }}>
          {error && (
            <Alert severity="error" onClose={() => setError('')}>
              {error}
            </Alert>
          )}

          <TextField
            label="Teacher ID"
            value={teacherId}
            onChange={(e) => setTeacherId(e.target.value)}
            required
            disabled={isEdit}
            helperText={isEdit ? 'Teacher ID cannot be changed' : 'Unique identifier for this teacher'}
            fullWidth
          />

          <TextField
            label="Display Name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="e.g., John Smith"
            fullWidth
          />

          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="teacher@school.com"
            fullWidth
          />

          {isEdit && (
            <FormControl fullWidth>
              <InputLabel>Status</InputLabel>
              <Select
                value={status}
                label="Status"
                onChange={(e: SelectChangeEvent) => setStatus(e.target.value)}
              >
                <MenuItem value="active">Active</MenuItem>
                <MenuItem value="inactive">Inactive</MenuItem>
                <MenuItem value="suspended">Suspended</MenuItem>
              </Select>
            </FormControl>
          )}

          <Divider />

          {/* AI Settings Section */}
          <Box>
            <Button
              startIcon={<SettingsIcon />}
              endIcon={showAISettings ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              onClick={() => setShowAISettings(!showAISettings)}
              sx={{ mb: 1 }}
            >
              AI Processing Settings
            </Button>

            <Collapse in={showAISettings}>
              <Stack spacing={2} sx={{ pl: 2, pt: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  Leave settings empty to use global defaults
                </Typography>

                <Box>
                  <Stack direction="row" alignItems="center" spacing={2}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={aiAutoProcessEnabled === true}
                          onChange={handleAIAutoProcessChange}
                        />
                      }
                      label={
                        aiAutoProcessEnabled === null
                          ? 'Auto-process (using default)'
                          : aiAutoProcessEnabled
                          ? 'Auto-process enabled'
                          : 'Auto-process disabled'
                      }
                    />
                    {aiAutoProcessEnabled !== null && (
                      <Button size="small" onClick={handleAIAutoProcessReset}>
                        Reset to default
                      </Button>
                    )}
                  </Stack>
                </Box>

                <FormControl fullWidth size="small">
                  <InputLabel>Processing Priority</InputLabel>
                  <Select
                    value={aiProcessingPriority}
                    label="Processing Priority"
                    onChange={(e: SelectChangeEvent) => setAiProcessingPriority(e.target.value)}
                  >
                    <MenuItem value="">
                      <em>Use default</em>
                    </MenuItem>
                    <MenuItem value="high">High</MenuItem>
                    <MenuItem value="normal">Normal</MenuItem>
                    <MenuItem value="low">Low</MenuItem>
                  </Select>
                </FormControl>

                <TextField
                  label="Audio Languages"
                  value={aiAudioLanguages}
                  onChange={(e) => setAiAudioLanguages(e.target.value)}
                  placeholder="e.g., en,tr"
                  helperText="Comma-separated language codes for audio generation"
                  size="small"
                  fullWidth
                />
              </Stack>
            </Collapse>
          </Box>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} variant="contained" disabled={loading}>
          {loading ? 'Saving...' : isEdit ? 'Save Changes' : 'Create Teacher'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TeacherFormDialog;
