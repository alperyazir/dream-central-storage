import { useEffect, useMemo, useState } from 'react';
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
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
  TextField
} from '@mui/material';
import RestoreFromTrashIcon from '@mui/icons-material/RestoreFromTrash';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';

import { ApiError } from '../lib/api';
import { deleteTrashEntry, restoreTrashEntry, listTrashEntries, TrashEntry } from '../lib/storage';
import { useAuthStore } from '../stores/auth';

import '../styles/page.css';

const formatBytes = (size?: number) => {
  if (typeof size !== 'number' || Number.isNaN(size)) {
    return '—';
  }

  if (size === 0) {
    return '0 B';
  }

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const exponent = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1);
  const value = size / Math.pow(1024, exponent);
  const precision = value >= 10 || exponent === 0 ? 0 : 1;
  return `${value.toFixed(precision)} ${units[exponent]}`;
};

const getEntryLabel = (entry: TrashEntry) => {
  if (entry.item_type === 'book' && entry.metadata) {
    const publisher = entry.metadata.publisher ?? entry.metadata.Publisher;
    const bookName = entry.metadata.book_name ?? entry.metadata.bookName;
    if (publisher && bookName) {
      return `${publisher} / ${bookName}`;
    }
  }

  if (entry.item_type === 'app' && entry.metadata) {
    const platform = entry.metadata.platform ?? entry.metadata.Platform;
    const version = entry.metadata.version ?? entry.metadata.Version;
    if (platform && version) {
      return `${platform} ${version}`;
    }
  }

  return entry.path || entry.key;
};

const pluralize = (value: number, unit: string) => `${value} ${unit}${value === 1 ? '' : 's'}`;

const formatDuration = (milliseconds: number) => {
  const totalSeconds = Math.max(Math.ceil(milliseconds / 1000), 0);
  const totalMinutes = Math.max(Math.ceil(totalSeconds / 60), 0);
  if (totalMinutes >= 1440) {
    return pluralize(Math.ceil(totalMinutes / 1440), 'day');
  }
  if (totalMinutes >= 60) {
    return pluralize(Math.ceil(totalMinutes / 60), 'hour');
  }
  return pluralize(Math.max(totalMinutes, 1), 'minute');
};

const formatDateTime = (value: Date) =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(value);

const formatTimeAgo = (value: Date, reference: Date) => {
  const diffMs = reference.getTime() - value.getTime();
  if (diffMs <= 0) {
    return 'moments ago';
  }
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) {
    return 'moments ago';
  }
  if (minutes < 60) {
    return `${pluralize(minutes, 'minute')} ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${pluralize(hours, 'hour')} ago`;
  }
  const days = Math.floor(hours / 24);
  return `${pluralize(days, 'day')} ago`;
};

interface RetentionState {
  label: string;
  tooltip: string;
  isEligible: boolean;
  eligibleAt: Date | null;
}

const getRetentionState = (entry: TrashEntry, reference: Date): RetentionState => {
  const eligibleAt = entry.eligible_at ? new Date(entry.eligible_at) : null;
  const youngest = entry.youngest_last_modified ? new Date(entry.youngest_last_modified) : null;
  let isEligible = entry.eligible_for_deletion ?? false;

  if (eligibleAt) {
    isEligible = eligibleAt.getTime() <= reference.getTime();
  }

  let label = isEligible ? 'Eligible now' : 'Eligibility pending';
  const tooltipParts: string[] = [];

  if (eligibleAt) {
    const diffMs = eligibleAt.getTime() - reference.getTime();
    if (diffMs <= 0) {
      label = 'Eligible now';
    } else {
      label = `Eligible in ${formatDuration(diffMs)}`;
    }
    tooltipParts.push(`Eligible on ${formatDateTime(eligibleAt)}.`);
  } else if (isEligible) {
    tooltipParts.push('Entry meets the retention requirement.');
  } else {
    tooltipParts.push('Retention metadata unavailable; refresh if eligibility seems outdated.');
  }

  if (youngest) {
    tooltipParts.push(`Newest object removed ${formatTimeAgo(youngest, reference)} (${formatDateTime(youngest)}).`);
  }

  const tooltip = tooltipParts.join(' ');

  return {
    label,
    tooltip,
    isEligible,
    eligibleAt
  };
};

const TrashPage = () => {
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType ?? 'Bearer');
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const [entries, setEntries] = useState<TrashEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [restoreTarget, setRestoreTarget] = useState<TrashEntry | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [isRestoring, setIsRestoring] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<TrashEntry | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [overrideCandidate, setOverrideCandidate] = useState<TrashEntry | null>(null);
  const [overrideTarget, setOverrideTarget] = useState<TrashEntry | null>(null);
  const [overrideReason, setOverrideReason] = useState('');
  const [overrideError, setOverrideError] = useState<string | null>(null);
  const [isOverrideDeleting, setIsOverrideDeleting] = useState(false);
  const [notification, setNotification] = useState<{ message: string; severity: 'success' | 'error' } | null>(null);
  const [refreshIndex, setRefreshIndex] = useState(0);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    let active = true;

    const fetchEntries = async () => {
      if (!isAuthenticated || !token) {
        if (active) {
          setEntries([]);
          setLoading(false);
        }
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const response = await listTrashEntries(token, tokenType);
        if (!active) {
          return;
        }
        setEntries(response);
      } catch (requestError) {
        if (!active) {
          return;
        }
        const message = requestError instanceof Error ? requestError.message : 'Unable to load trash contents.';
        setError(message);
        setEntries([]);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void fetchEntries();

    return () => {
      active = false;
    };
  }, [isAuthenticated, token, tokenType, refreshIndex]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }
    const intervalId = window.setInterval(() => {
      setNow(new Date());
    }, 60000);
    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

  const openRestoreDialog = (entry: TrashEntry) => {
    setRestoreTarget(entry);
    setRestoreError(null);
  };

  const closeRestoreDialog = () => {
    if (isRestoring) {
      return;
    }
    setRestoreTarget(null);
  };

  const openDeleteDialog = (entry: TrashEntry) => {
    setDeleteTarget(entry);
    setDeleteError(null);
    setOverrideCandidate(null);
    setOverrideTarget(null);
    setOverrideReason('');
    setOverrideError(null);
  };

  const closeDeleteDialog = () => {
    if (isDeleting) {
      return;
    }
    setDeleteTarget(null);
    setDeleteError(null);
    setOverrideCandidate(null);
  };

  const openOverrideDialog = () => {
    if (!overrideCandidate) {
      return;
    }
    setOverrideTarget(overrideCandidate);
    setOverrideReason('');
    setOverrideError(null);
    setOverrideCandidate(null);
    setDeleteTarget(null);
  };

  const openOverrideDialogForEntry = (entry: TrashEntry) => {
    setOverrideTarget(entry);
    setOverrideReason('');
    setOverrideError(null);
    setOverrideCandidate(null);
    setDeleteTarget(null);
  };

  const closeOverrideDialog = () => {
    if (isOverrideDeleting) {
      return;
    }
    setOverrideTarget(null);
    setOverrideReason('');
    setOverrideError(null);
  };

  const performRestore = async () => {
    if (!restoreTarget || !token) {
      return;
    }

    setIsRestoring(true);
    setRestoreError(null);

    try {
      await restoreTrashEntry(restoreTarget.key, token, tokenType);
      setRestoreTarget(null);
      setRefreshIndex((value) => value + 1);
    } catch (requestError) {
      if (requestError instanceof Error) {
        console.error('Failed to restore trash entry', requestError);
      }
      setRestoreError('Unable to restore the selected item.');
    } finally {
      setIsRestoring(false);
    }
  };

  const sortedEntries = useMemo(() => {
    return [...entries].sort((a, b) => getEntryLabel(a).localeCompare(getEntryLabel(b), undefined, { sensitivity: 'base' }));
  }, [entries]);

  const performPermanentDelete = async () => {
    if (!deleteTarget || !token) {
      return;
    }

    setDeleteError(null);

    const retention = getRetentionState(deleteTarget, new Date());
    if (!retention.isEligible) {
      const guidance = retention.eligibleAt
        ? `This entry becomes eligible on ${formatDateTime(retention.eligibleAt)}.`
        : 'This entry is still within the retention window.';
      setDeleteError(guidance);
      setOverrideCandidate(deleteTarget);
      return;
    }

    setIsDeleting(true);
    setOverrideCandidate(null);

    try {
      const label = getEntryLabel(deleteTarget);
      await deleteTrashEntry(deleteTarget.key, token, tokenType);
      setDeleteTarget(null);
      setNotification({ severity: 'success', message: `Permanently deleted "${label}".` });
      setRefreshIndex((value) => value + 1);
    } catch (requestError) {
      if (requestError instanceof Error) {
        console.error('Failed to permanently delete trash entry', requestError);
      }

      let message = 'Unable to permanently delete the selected item.';
      if (requestError instanceof ApiError) {
        const detail = (requestError.body as { detail?: string } | null)?.detail;
        if (typeof detail === 'string' && detail.trim().length > 0) {
          message = detail;
        }
        if (requestError.status === 409 && deleteTarget) {
          setOverrideCandidate(deleteTarget);
        }
      } else if (requestError instanceof Error && requestError.message) {
        message = requestError.message;
      }

      setDeleteError(message);
    } finally {
      setIsDeleting(false);
    }
  };

  const performOverrideDelete = async () => {
    if (!overrideTarget || !token) {
      return;
    }

    const trimmedReason = overrideReason.trim();
    if (!trimmedReason) {
      setOverrideError('Please provide a justification for the override.');
      return;
    }

    setIsOverrideDeleting(true);
    setOverrideError(null);

    try {
      const label = getEntryLabel(overrideTarget);
      await deleteTrashEntry(overrideTarget.key, token, tokenType, undefined, {
        force: true,
        overrideReason: trimmedReason
      });
      setOverrideTarget(null);
      setOverrideReason('');
      setNotification({ severity: 'success', message: `Override deletion completed for "${label}".` });
      setRefreshIndex((value) => value + 1);
    } catch (requestError) {
      if (requestError instanceof Error) {
        console.error('Failed to override retention for trash entry', requestError);
      }

      let message = 'Unable to override the retention window.';
      if (requestError instanceof ApiError) {
        const detail = (requestError.body as { detail?: string } | null)?.detail;
        if (typeof detail === 'string' && detail.trim().length > 0) {
          message = detail;
        }
      } else if (requestError instanceof Error && requestError.message) {
        message = requestError.message;
      }

      setOverrideError(message);
    } finally {
      setIsOverrideDeleting(false);
    }
  };

  const restoreDialog = (
    <Dialog
      open={Boolean(restoreTarget)}
      onClose={closeRestoreDialog}
      aria-labelledby="trash-restore-dialog-title"
      aria-describedby="trash-restore-dialog-description"
    >
      <DialogTitle id="trash-restore-dialog-title">Confirm Restore</DialogTitle>
      <DialogContent>
        <DialogContentText id="trash-restore-dialog-description">
          {restoreTarget
            ? `Restore "${getEntryLabel(restoreTarget)}" to ${restoreTarget.bucket} / ${restoreTarget.path}?`
            : ''}
        </DialogContentText>
        {restoreError ? (
          <Alert severity="error" sx={{ mt: 2 }}>
            {restoreError}
          </Alert>
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button onClick={closeRestoreDialog} disabled={isRestoring}>
          Cancel
        </Button>
        <Button onClick={performRestore} color="primary" disabled={isRestoring || isDeleting}>
          {isRestoring ? 'Restoring…' : 'Restore'}
        </Button>
      </DialogActions>
    </Dialog>
  );

  const deleteDialog = (
    <Dialog
      open={Boolean(deleteTarget)}
      onClose={closeDeleteDialog}
      aria-labelledby="trash-delete-dialog-title"
      aria-describedby="trash-delete-dialog-description"
    >
      <DialogTitle id="trash-delete-dialog-title">Delete Permanently</DialogTitle>
      <DialogContent>
        <DialogContentText id="trash-delete-dialog-description">
          {deleteTarget
            ? `Permanently delete "${getEntryLabel(deleteTarget)}"? This action cannot be undone.`
            : ''}
        </DialogContentText>
        {deleteError ? (
          <Alert severity="error" sx={{ mt: 2 }}>
            {deleteError}
          </Alert>
        ) : null}
        {overrideCandidate?.key === deleteTarget?.key ? (
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
            <Button onClick={openOverrideDialog} variant="outlined" disabled={isDeleting || isRestoring}>
              Override retention
            </Button>
          </Box>
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button onClick={closeDeleteDialog} disabled={isDeleting}>
          Cancel
        </Button>
        <Button onClick={performPermanentDelete} color="error" disabled={isDeleting || isRestoring}>
          {isDeleting ? 'Deleting…' : 'Delete'}
        </Button>
      </DialogActions>
    </Dialog>
  );

  const overrideDialog = (
    <Dialog
      open={Boolean(overrideTarget)}
      onClose={closeOverrideDialog}
      aria-labelledby="trash-override-dialog-title"
      aria-describedby="trash-override-dialog-description"
    >
      <DialogTitle id="trash-override-dialog-title">Override Retention</DialogTitle>
      <DialogContent>
        <DialogContentText id="trash-override-dialog-description">
          {overrideTarget
            ? `Provide a justification to permanently delete "${getEntryLabel(overrideTarget)}" before the retention period ends.`
            : ''}
        </DialogContentText>
        <TextField
          autoFocus
          fullWidth
          multiline
          minRows={3}
          margin="normal"
          label="Override justification"
          placeholder="Explain the compliance approval or reason for the early deletion"
          value={overrideReason}
          onChange={(event) => setOverrideReason(event.target.value)}
          disabled={isOverrideDeleting}
        />
        {overrideError ? (
          <Alert severity="error" sx={{ mt: 2 }}>
            {overrideError}
          </Alert>
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button onClick={closeOverrideDialog} disabled={isOverrideDeleting}>
          Cancel
        </Button>
        <Button onClick={performOverrideDelete} color="error" disabled={isOverrideDeleting}>
          {isOverrideDeleting ? 'Overriding…' : 'Override deletion'}
        </Button>
      </DialogActions>
    </Dialog>
  );

  const hasEntries = sortedEntries.length > 0;
  const isInitialLoad = loading && !hasEntries && !error;

  return (
    <section className="page" aria-busy={loading} aria-live="polite">
      <Typography variant="h4" component="h1" gutterBottom>
        Trash
      </Typography>
      <Typography variant="body1" paragraph>
        Review items moved to the trash bucket. Restoring an entry will return it to its original location.
      </Typography>

      {loading ? (
        <Alert severity="info" sx={{ mb: 3 }} role="status">
          Refreshing trash contents…
        </Alert>
      ) : null}

      {error ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      ) : null}

      {notification ? (
        <Alert severity={notification.severity} sx={{ mb: 3 }} onClose={() => setNotification(null)}>
          {notification.message}
        </Alert>
      ) : null}

      {!loading && !error && !hasEntries ? (
        <Alert severity="info" sx={{ mb: 3 }}>
          Trash is currently empty.
        </Alert>
      ) : null}

      {isInitialLoad ? (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 4 }}>
          <CircularProgress aria-label="Loading trash entries" />
          <Typography variant="body1">Loading trash entries…</Typography>
        </Box>
      ) : null}

      {hasEntries ? (
        <TableContainer component={Paper} sx={{ mt: 3 }}>
          <Table aria-label="Trash entries table">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Bucket</TableCell>
                <TableCell>Path</TableCell>
                <TableCell align="right">Objects</TableCell>
                <TableCell align="right">Size</TableCell>
                <TableCell align="right">Retention</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedEntries.map((entry) => {
                const retention = getRetentionState(entry, now);
                const deleteDisabled = isDeleting || isRestoring || !retention.isEligible;
                const deleteTooltip = retention.isEligible ? 'Delete permanently' : retention.tooltip;
                const overrideDisabled = isDeleting || isRestoring;

                return (
                  <TableRow key={entry.key} hover>
                    <TableCell>{getEntryLabel(entry)}</TableCell>
                    <TableCell>{entry.bucket}</TableCell>
                    <TableCell>{entry.path}</TableCell>
                    <TableCell align="right">{entry.object_count}</TableCell>
                    <TableCell align="right">{formatBytes(entry.total_size)}</TableCell>
                    <TableCell align="right">
                      <Tooltip title={retention.tooltip}>
                        <Typography
                          variant="body2"
                          component="span"
                          sx={{ color: retention.isEligible ? 'success.main' : 'warning.main' }}
                        >
                          {retention.label}
                        </Typography>
                      </Tooltip>
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, flexWrap: 'wrap' }}>
                        <Tooltip title="Restore item">
                          <span>
                            <Button
                              variant="outlined"
                              size="small"
                              startIcon={<RestoreFromTrashIcon fontSize="small" />}
                              onClick={() => openRestoreDialog(entry)}
                              disabled={isRestoring || isDeleting}
                            >
                              Restore
                            </Button>
                          </span>
                        </Tooltip>
                        <Tooltip title={deleteTooltip}>
                          <span>
                            <Button
                              variant="contained"
                              color="error"
                              size="small"
                              startIcon={<DeleteForeverIcon fontSize="small" />}
                              onClick={() => openDeleteDialog(entry)}
                              disabled={deleteDisabled}
                            >
                              Delete
                            </Button>
                          </span>
                        </Tooltip>
                        {!retention.isEligible ? (
                          <Tooltip title="Request retention override">
                            <span>
                              <Button
                                variant="outlined"
                                color="warning"
                                size="small"
                                onClick={() => openOverrideDialogForEntry(entry)}
                                disabled={overrideDisabled}
                              >
                                Override
                              </Button>
                            </span>
                          </Tooltip>
                        ) : null}
                      </Box>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      ) : null}

      {restoreDialog}
      {deleteDialog}
      {overrideDialog}
    </section>
  );
};

export default TrashPage;
