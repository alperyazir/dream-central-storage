import { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  SelectChangeEvent,
  Stack,
  Typography,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';

import {
  triggerProcessing,
  getProcessingStatus,
  deleteAIData,
  ProcessingJobType,
  ProcessingStatusResponse,
  getStatusColor,
  getStatusLabel,
} from '../lib/processing';
import { ApiError } from '../lib/api';

interface ProcessingDialogProps {
  open: boolean;
  onClose: () => void;
  bookId: number;
  bookTitle: string;
  token: string | null;
  tokenType: string | null;
}

// Helper to check if text extraction is done
const hasTextExtraction = (currentStep: string | undefined): boolean => {
  if (!currentStep) return false;
  // If we're past text_extraction or the step mentions analysis/vocabulary/audio
  const completedIndicators = ['analysis', 'vocabulary', 'audio', 'chunked', 'unified'];
  return completedIndicators.some(indicator => currentStep.toLowerCase().includes(indicator));
};

// Helper to check if LLM analysis is done
const hasLLMAnalysis = (currentStep: string | undefined): boolean => {
  if (!currentStep) return false;
  // If we're at audio generation, LLM is done
  return currentStep.toLowerCase().includes('audio');
};

const ProcessingDialog = ({
  open,
  onClose,
  bookId,
  bookTitle,
  token,
  tokenType,
}: ProcessingDialogProps) => {
  const [jobType, setJobType] = useState<ProcessingJobType>('full');
  const [status, setStatus] = useState<ProcessingStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Fetch current status when dialog opens
  useEffect(() => {
    if (open && token) {
      fetchStatus();
    }
  }, [open, bookId, token]);

  // Poll for status updates when processing
  useEffect(() => {
    if (!polling || !token || !open) return;

    const interval = setInterval(() => {
      fetchStatus();
    }, 3000);

    return () => clearInterval(interval);
  }, [polling, token, open]);

  // Stop polling when completed/failed
  useEffect(() => {
    if (status?.status === 'completed' || status?.status === 'failed' || status?.status === 'cancelled') {
      setPolling(false);
    }
  }, [status?.status]);

  const fetchStatus = async () => {
    if (!token) return;

    try {
      const result = await getProcessingStatus(bookId, token, tokenType || 'Bearer');
      setStatus(result);
      if (result.status === 'queued' || result.status === 'processing') {
        setPolling(true);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setStatus(null);
      } else {
        console.error('Failed to fetch status:', err);
      }
    }
  };

  const handleTrigger = async () => {
    if (!token) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await triggerProcessing(bookId, token, tokenType || 'Bearer', {
        job_type: jobType,
        admin_override: true,
      });
      setStatus({
        job_id: result.job_id,
        book_id: result.book_id,
        status: result.status,
        progress: result.progress,
        current_step: result.current_step,
        error_message: result.error_message,
        created_at: result.created_at,
        started_at: result.started_at,
        completed_at: result.completed_at,
      });
      setSuccess('Processing started successfully!');
      setPolling(true);
    } catch (err) {
      if (err instanceof ApiError) {
        const body = err.body as { detail?: string };
        setError(body?.detail || `Error: ${err.status}`);
      } else {
        setError('Failed to trigger processing');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleClearAndReprocess = async () => {
    if (!token) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await deleteAIData(bookId, token, tokenType || 'Bearer', true);
      setSuccess('AI data cleared and reprocessing started!');
      // Fetch the new status
      setTimeout(fetchStatus, 1000);
      setPolling(true);
    } catch (err) {
      if (err instanceof ApiError) {
        const body = err.body as { detail?: string };
        setError(body?.detail || `Error: ${err.status}`);
      } else {
        setError('Failed to clear AI data');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setPolling(false);
    setError(null);
    setSuccess(null);
    onClose();
  };

  const isProcessing = status?.status === 'queued' || status?.status === 'processing';

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>AI Processing - {bookTitle}</DialogTitle>
      <DialogContent>
        <Stack spacing={3} sx={{ mt: 1 }}>
          {/* Current Status */}
          {status && (
            <Box>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Current Status
              </Typography>
              <Stack direction="row" spacing={2} alignItems="center">
                <Chip
                  label={getStatusLabel(status.status)}
                  color={getStatusColor(status.status)}
                  size="small"
                />
                {status.current_step && (
                  <Typography variant="body2" color="text.secondary">
                    Step: {status.current_step}
                  </Typography>
                )}
              </Stack>

              {isProcessing && (
                <Box sx={{ mt: 2 }}>
                  <LinearProgress
                    variant="determinate"
                    value={status.progress}
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                    {status.progress}% complete
                  </Typography>
                  {/* Show detailed step info for chunked analysis */}
                  {status.current_step && status.current_step.includes('Extracting vocabulary:') && (
                    <Alert severity="info" sx={{ mt: 1, py: 0.5 }}>
                      <Typography variant="caption">
                        {status.current_step}
                      </Typography>
                    </Alert>
                  )}
                </Box>
              )}

              {status.error_message && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {status.error_message}
                </Alert>
              )}

              {status.status === 'completed' && (
                <Alert severity="success" sx={{ mt: 2 }}>
                  Processing completed successfully!
                </Alert>
              )}
            </Box>
          )}

          {!status && (
            <Alert severity="info">
              No AI processing has been run for this book yet.
            </Alert>
          )}

          {/* Trigger Options */}
          {!isProcessing && (
            <Box>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Start New Processing
              </Typography>

              <FormControl fullWidth size="small" sx={{ mt: 1 }}>
                <InputLabel>Processing Type</InputLabel>
                <Select
                  value={jobType}
                  label="Processing Type"
                  onChange={(e: SelectChangeEvent) => setJobType(e.target.value as ProcessingJobType)}
                >
                  <MenuItem value="full">
                    Full Process (Text + AI + Audio)
                  </MenuItem>
                  <MenuItem value="text_only">
                    Text Extraction Only
                  </MenuItem>
                  <MenuItem
                    value="llm_only"
                    disabled={status?.status !== 'completed' && !hasTextExtraction(status?.current_step)}
                  >
                    AI Analysis Only {status?.status !== 'completed' && !hasTextExtraction(status?.current_step) ? '(requires text extraction)' : ''}
                  </MenuItem>
                  <MenuItem
                    value="audio_only"
                    disabled={status?.status !== 'completed' && !hasLLMAnalysis(status?.current_step)}
                  >
                    Audio Generation Only {status?.status !== 'completed' && !hasLLMAnalysis(status?.current_step) ? '(requires AI analysis)' : ''}
                  </MenuItem>
                </Select>
              </FormControl>

              {/* Show info about chunked processing */}
              {(jobType === 'full' || jobType === 'llm_only') && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  AI Analysis uses a two-phase chunked approach:
                  <br />
                  1. Detect all modules/chapters
                  <br />
                  2. Extract vocabulary per module (with retries)
                </Alert>
              )}

              <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
                <Button
                  variant="contained"
                  startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
                  onClick={handleTrigger}
                  disabled={loading}
                >
                  Start Processing
                </Button>

                {status && (
                  <Button
                    variant="outlined"
                    color="warning"
                    startIcon={<DeleteSweepIcon />}
                    onClick={handleClearAndReprocess}
                    disabled={loading}
                  >
                    Clear & Reprocess
                  </Button>
                )}
              </Stack>
            </Box>
          )}

          {/* Messages */}
          {error && (
            <Alert severity="error" onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {success && (
            <Alert severity="success" onClose={() => setSuccess(null)}>
              {success}
            </Alert>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={fetchStatus} startIcon={<RefreshIcon />} disabled={loading}>
          Refresh Status
        </Button>
        <Button onClick={handleClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default ProcessingDialog;
