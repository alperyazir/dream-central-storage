import { useEffect, useState, useCallback } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
} from '@mui/material';

import { createPublisher, updatePublisher, Publisher, PublisherCreate, PublisherUpdate } from '../lib/publishers';
import {
  getPublisherProcessingSettings,
  updatePublisherProcessingSettings,
  PublisherProcessingSettingsUpdate,
} from '../lib/processing';
import { ApiError } from '../lib/api';

interface PublisherFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  publisher?: Publisher | null;
  token: string | null;
  tokenType: string | null;
}

const deriveErrorMessage = (error: unknown): string => {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: unknown } | null)?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    return `Operation failed (${error.status}). Please try again.`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Operation failed. Please try again.';
};

const PublisherFormDialog = ({
  open,
  onClose,
  onSuccess,
  publisher,
  token,
  tokenType,
}: PublisherFormDialogProps) => {
  const isEdit = !!publisher;

  const [name, setName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [description, setDescription] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [status, setStatus] = useState<'active' | 'inactive' | 'suspended'>('active');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [emailError, setEmailError] = useState('');

  // AI Processing Settings (null = use global default)
  const [aiAutoProcess, setAiAutoProcess] = useState<boolean | null>(null);
  const [aiPriority, setAiPriority] = useState<'high' | 'normal' | 'low' | null>(null);
  const [aiAudioLanguages, setAiAudioLanguages] = useState<string | null>(null);
  const [aiSettingsLoading, setAiSettingsLoading] = useState(false);

  const LANGUAGE_OPTIONS = [
    { value: 'en', label: 'English' },
    { value: 'tr', label: 'Turkish' },
    { value: 'de', label: 'German' },
    { value: 'fr', label: 'French' },
    { value: 'es', label: 'Spanish' },
  ];

  const loadAiSettings = useCallback(async () => {
    if (!publisher || !token) return;
    setAiSettingsLoading(true);
    try {
      const settings = await getPublisherProcessingSettings(publisher.id, token, tokenType || 'Bearer');
      setAiAutoProcess(settings.ai_auto_process_enabled);
      setAiPriority(settings.ai_processing_priority);
      setAiAudioLanguages(settings.ai_audio_languages);
    } catch (err) {
      console.error('Failed to load AI settings:', err);
      // Don't block the form if AI settings fail to load
    } finally {
      setAiSettingsLoading(false);
    }
  }, [publisher, token, tokenType]);

  useEffect(() => {
    if (publisher) {
      setName(publisher.name);
      setDisplayName(publisher.display_name || '');
      setDescription(publisher.description || '');
      setContactEmail(publisher.contact_email || '');
      setStatus(publisher.status);
      // Load AI settings for edit mode
      loadAiSettings();
    } else {
      setName('');
      setDisplayName('');
      setDescription('');
      setContactEmail('');
      setStatus('active');
      // Reset AI settings for create mode
      setAiAutoProcess(null);
      setAiPriority(null);
      setAiAudioLanguages(null);
    }
    setError('');
    setEmailError('');
  }, [publisher, open, loadAiSettings]);

  const validateEmail = (email: string): boolean => {
    if (!email) return true; // Email is optional
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleEmailChange = (value: string) => {
    setContactEmail(value);
    if (value && !validateEmail(value)) {
      setEmailError('Please enter a valid email address');
    } else {
      setEmailError('');
    }
  };

  const handleSubmit = async () => {
    if (!token) return;

    // Validation
    if (!name.trim()) {
      setError('Name is required');
      return;
    }

    if (contactEmail && !validateEmail(contactEmail)) {
      setEmailError('Please enter a valid email address');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      let publisherId: number;

      if (isEdit && publisher) {
        const data: PublisherUpdate = {
          name: name.trim(),
          display_name: displayName.trim() || undefined,
          description: description.trim() || undefined,
          contact_email: contactEmail.trim() || undefined,
          status,
        };
        await updatePublisher(publisher.id, data, token, tokenType || 'Bearer');
        publisherId = publisher.id;
      } else {
        const data: PublisherCreate = {
          name: name.trim(),
          display_name: displayName.trim() || undefined,
          description: description.trim() || undefined,
          contact_email: contactEmail.trim() || undefined,
          status,
        };
        const created = await createPublisher(data, token, tokenType || 'Bearer');
        publisherId = created.id;
      }

      // Save AI processing settings
      const aiSettings: PublisherProcessingSettingsUpdate = {
        ai_auto_process_enabled: aiAutoProcess,
        ai_processing_priority: aiPriority,
        ai_audio_languages: aiAudioLanguages,
      };
      await updatePublisherProcessingSettings(publisherId, aiSettings, token, tokenType || 'Bearer');

      onSuccess();
    } catch (err) {
      console.error('Failed to save publisher:', err);
      setError(deriveErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!submitting) {
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? 'Edit Publisher' : 'Add New Publisher'}</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {isEdit
            ? 'Update publisher information below.'
            : 'Fill in the details to create a new publisher.'}
        </Typography>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            fullWidth
            disabled={submitting}
            helperText="Internal identifier (e.g., 'noor-publishing')"
          />

          <TextField
            label="Display Name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            fullWidth
            disabled={submitting}
            helperText="User-friendly name (e.g., 'Noor Publishing')"
          />

          <TextField
            label="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            fullWidth
            multiline
            rows={3}
            disabled={submitting}
          />

          <TextField
            label="Contact Email"
            type="email"
            value={contactEmail}
            onChange={(e) => handleEmailChange(e.target.value)}
            fullWidth
            disabled={submitting}
            error={!!emailError}
            helperText={emailError || 'Optional contact email'}
          />

          <FormControl fullWidth disabled={submitting}>
            <InputLabel>Status</InputLabel>
            <Select
              value={status}
              label="Status"
              onChange={(e) => setStatus(e.target.value as 'active' | 'inactive' | 'suspended')}
            >
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="inactive">Inactive</MenuItem>
              <MenuItem value="suspended">Suspended</MenuItem>
            </Select>
          </FormControl>

          {/* AI Processing Settings */}
          <Divider sx={{ my: 1 }} />
          <Typography variant="subtitle2" color="text.secondary">
            AI Processing Settings
            {aiSettingsLoading && <Chip label="Loading..." size="small" sx={{ ml: 1 }} />}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
            Leave settings as &quot;Use Global Default&quot; to inherit from global configuration.
          </Typography>

          <FormControl fullWidth disabled={submitting || aiSettingsLoading}>
            <InputLabel>Auto-Process on Upload</InputLabel>
            <Select
              value={aiAutoProcess === null ? 'default' : aiAutoProcess ? 'enabled' : 'disabled'}
              label="Auto-Process on Upload"
              onChange={(e) => {
                const val = e.target.value;
                setAiAutoProcess(val === 'default' ? null : val === 'enabled');
              }}
            >
              <MenuItem value="default">Use Global Default</MenuItem>
              <MenuItem value="enabled">Enabled</MenuItem>
              <MenuItem value="disabled">Disabled</MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth disabled={submitting || aiSettingsLoading}>
            <InputLabel>Processing Priority</InputLabel>
            <Select
              value={aiPriority || 'default'}
              label="Processing Priority"
              onChange={(e) => {
                const val = e.target.value;
                setAiPriority(val === 'default' ? null : (val as 'high' | 'normal' | 'low'));
              }}
            >
              <MenuItem value="default">Use Global Default</MenuItem>
              <MenuItem value="high">High</MenuItem>
              <MenuItem value="normal">Normal</MenuItem>
              <MenuItem value="low">Low</MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth disabled={submitting || aiSettingsLoading}>
            <InputLabel>Audio Languages</InputLabel>
            <Select
              multiple
              value={aiAudioLanguages ? aiAudioLanguages.split(',').filter(Boolean) : []}
              label="Audio Languages"
              onChange={(e) => {
                const value = e.target.value;
                const langs = Array.isArray(value) ? value : [value];
                setAiAudioLanguages(langs.length > 0 ? langs.join(',') : null);
              }}
              renderValue={(selected) => {
                if (selected.length === 0) {
                  return <em>Use Global Default</em>;
                }
                return selected
                  .map((v) => LANGUAGE_OPTIONS.find((l) => l.value === v)?.label || v)
                  .join(', ');
              }}
            >
              {LANGUAGE_OPTIONS.map((lang) => (
                <MenuItem key={lang.value} value={lang.value}>
                  {lang.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Typography variant="caption" color="text.secondary">
            Select specific languages or leave empty to use global default.
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={submitting}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={submitting || !name.trim() || !!emailError}
        >
          {submitting ? 'Saving...' : isEdit ? 'Update' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PublisherFormDialog;
