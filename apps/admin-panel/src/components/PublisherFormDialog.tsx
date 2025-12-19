import { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
} from '@mui/material';

import { createPublisher, updatePublisher, Publisher, PublisherCreate, PublisherUpdate } from '../lib/publishers';
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

  useEffect(() => {
    if (publisher) {
      setName(publisher.name);
      setDisplayName(publisher.display_name || '');
      setDescription(publisher.description || '');
      setContactEmail(publisher.contact_email || '');
      setStatus(publisher.status);
    } else {
      setName('');
      setDisplayName('');
      setDescription('');
      setContactEmail('');
      setStatus('active');
    }
    setError('');
    setEmailError('');
  }, [publisher, open]);

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
      if (isEdit && publisher) {
        const data: PublisherUpdate = {
          name: name.trim(),
          display_name: displayName.trim() || undefined,
          description: description.trim() || undefined,
          contact_email: contactEmail.trim() || undefined,
          status,
        };
        await updatePublisher(publisher.id, data, token, tokenType || 'Bearer');
      } else {
        const data: PublisherCreate = {
          name: name.trim(),
          display_name: displayName.trim() || undefined,
          description: description.trim() || undefined,
          contact_email: contactEmail.trim() || undefined,
          status,
        };
        await createPublisher(data, token, tokenType || 'Bearer');
      }
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
