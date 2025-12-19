import { ChangeEvent, useEffect, useReducer, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormHelperText,
  LinearProgress,
  Radio,
  RadioGroup,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';

import { fetchPublishers, Publisher, uploadPublisherAsset } from '../lib/publishers';
import { uploadNewBookArchive } from '../lib/uploads';
import { ApiError } from '../lib/api';

interface PublisherUploadDialogProps {
  open: boolean;
  onClose: () => void;
  token: string | null;
  tokenType: string | null;
  onSuccess: () => void;
  initialPublisherId?: number;
}

type UploadStep = 'publisher' | 'content-type' | 'files' | 'uploading' | 'success' | 'error';

interface UploadState {
  step: UploadStep;
  publisherId: number | null;
  contentType: string | null;
  customContentType: string;
  files: File[];
  progress: Map<string, number>;
  error: string | null;
  uploadResults: UploadResult[];
}

interface UploadResult {
  filename: string;
  success: boolean;
  error?: string;
  path?: string;
}

type UploadAction =
  | { type: 'SET_PUBLISHER'; publisherId: number }
  | { type: 'SET_CONTENT_TYPE'; contentType: string }
  | { type: 'SET_CUSTOM_CONTENT_TYPE'; customContentType: string }
  | { type: 'SET_FILES'; files: File[] }
  | { type: 'START_UPLOAD' }
  | { type: 'UPLOAD_SUCCESS'; results: UploadResult[] }
  | { type: 'UPLOAD_ERROR'; error: string }
  | { type: 'NEXT_STEP' }
  | { type: 'PREV_STEP' }
  | { type: 'RESET' };

// Content type validation rules
const CONTENT_TYPE_RULES: Record<string, {
  accept: string;
  maxSize: number;
  multiple: boolean;
  acceptedFormats: string;
}> = {
  books: {
    accept: '.zip',
    maxSize: 500 * 1024 * 1024, // 500MB
    multiple: true,
    acceptedFormats: '.zip',
  },
  materials: {
    accept: '.pdf,.docx,.pptx,.jpg,.jpeg,.png,.gif,.mp3,.mp4',
    maxSize: 100 * 1024 * 1024, // 100MB
    multiple: true,
    acceptedFormats: '.pdf, .docx, .pptx, images, audio, video',
  },
  logos: {
    accept: '.png,.jpg,.jpeg,.svg',
    maxSize: 5 * 1024 * 1024, // 5MB
    multiple: false,
    acceptedFormats: '.png, .jpg, .svg',
  },
  default: {
    accept: '*',
    maxSize: 100 * 1024 * 1024,
    multiple: true,
    acceptedFormats: 'All common formats',
  },
};

const RESERVED_ASSET_TYPES = ['trash', 'temp', 'books'];
const PREDEFINED_TYPES = ['books', 'materials', 'logos'];

const uploadReducer = (state: UploadState, action: UploadAction): UploadState => {
  switch (action.type) {
    case 'SET_PUBLISHER':
      return { ...state, publisherId: action.publisherId };
    case 'SET_CONTENT_TYPE':
      return { ...state, contentType: action.contentType, customContentType: '' };
    case 'SET_CUSTOM_CONTENT_TYPE':
      return { ...state, customContentType: action.customContentType };
    case 'SET_FILES':
      return { ...state, files: action.files };
    case 'START_UPLOAD':
      return { ...state, step: 'uploading', error: null };
    case 'UPLOAD_SUCCESS':
      return { ...state, step: 'success', uploadResults: action.results };
    case 'UPLOAD_ERROR':
      return { ...state, step: 'error', error: action.error };
    case 'NEXT_STEP': {
      const stepOrder: UploadStep[] = ['publisher', 'content-type', 'files'];
      const currentIndex = stepOrder.indexOf(state.step);
      return currentIndex < stepOrder.length - 1
        ? { ...state, step: stepOrder[currentIndex + 1] }
        : state;
    }
    case 'PREV_STEP': {
      const prevStepOrder: UploadStep[] = ['publisher', 'content-type', 'files'];
      const prevIndex = prevStepOrder.indexOf(state.step);
      return prevIndex > 0
        ? { ...state, step: prevStepOrder[prevIndex - 1] }
        : state;
    }
    case 'RESET':
      return {
        step: 'publisher',
        publisherId: null,
        contentType: null,
        customContentType: '',
        files: [],
        progress: new Map(),
        error: null,
        uploadResults: [],
      };
    default:
      return state;
  }
};

const deriveErrorMessage = (error: unknown): string => {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: unknown } | null)?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    return `Upload failed (${error.status}). Please try again.`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Upload failed. Please try again.';
};

const PublisherUploadDialog = ({
  open,
  onClose,
  token,
  tokenType,
  onSuccess,
  initialPublisherId,
}: PublisherUploadDialogProps) => {
  const [state, dispatch] = useReducer(uploadReducer, {
    step: initialPublisherId ? 'content-type' : 'publisher',
    publisherId: initialPublisherId || null,
    contentType: null,
    customContentType: '',
    files: [],
    progress: new Map(),
    error: null,
    uploadResults: [],
  });

  const [publishers, setPublishers] = useState<Publisher[]>([]);
  const [loadingPublishers, setLoadingPublishers] = useState(false);
  const [publisherError, setPublisherError] = useState('');
  const [customTypeError, setCustomTypeError] = useState('');
  const [fileError, setFileError] = useState('');

  // Load publishers - always fetch when dialog opens
  useEffect(() => {
    if (open && token) {
      setLoadingPublishers(true);
      fetchPublishers(token, tokenType || 'Bearer')
        .then((data) => {
          setPublishers(data);
          // If initialPublisherId is provided, ensure it's set in state
          if (initialPublisherId) {
            dispatch({ type: 'SET_PUBLISHER', publisherId: initialPublisherId });
          }
        })
        .catch((err) => {
          setPublisherError(deriveErrorMessage(err));
        })
        .finally(() => setLoadingPublishers(false));
    }
  }, [open, token, tokenType, initialPublisherId]);

  // Reset on close
  useEffect(() => {
    if (!open) {
      dispatch({ type: 'RESET' });
      setCustomTypeError('');
      setFileError('');
      setPublisherError('');
    }
  }, [open]);

  const selectedPublisher = publishers.find((p) => p.id === state.publisherId);

  const validateCustomContentType = (value: string): boolean => {
    if (!value.trim()) {
      setCustomTypeError('Content type is required');
      return false;
    }
    if (!/^[a-z0-9_-]+$/i.test(value)) {
      setCustomTypeError('Only alphanumeric characters, hyphens, and underscores allowed');
      return false;
    }
    if (RESERVED_ASSET_TYPES.includes(value.toLowerCase())) {
      setCustomTypeError(`"${value}" is a reserved name and cannot be used`);
      return false;
    }
    setCustomTypeError('');
    return true;
  };

  const getContentTypeRules = () => {
    const type = state.contentType === 'custom'
      ? state.customContentType.toLowerCase()
      : state.contentType;
    return CONTENT_TYPE_RULES[type || 'default'] || CONTENT_TYPE_RULES.default;
  };

  const validateFiles = (files: File[]): boolean => {
    const rules = getContentTypeRules();

    if (!rules.multiple && files.length > 1) {
      setFileError(`Only one file allowed for ${state.contentType} uploads`);
      return false;
    }

    for (const file of files) {
      if (file.size > rules.maxSize) {
        const maxSizeMB = rules.maxSize / (1024 * 1024);
        setFileError(`File "${file.name}" exceeds maximum size of ${maxSizeMB}MB`);
        return false;
      }

      if (rules.accept !== '*') {
        const acceptedExtensions = rules.accept.split(',');
        const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
        if (!acceptedExtensions.includes(fileExtension)) {
          setFileError(`File type not allowed. Accepted formats: ${rules.acceptedFormats}`);
          return false;
        }
      }
    }

    setFileError('');
    return true;
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = event.target.files;
    if (selectedFiles && selectedFiles.length > 0) {
      const filesArray = Array.from(selectedFiles);
      if (validateFiles(filesArray)) {
        dispatch({ type: 'SET_FILES', files: filesArray });
      }
    }
  };

  const handleNext = () => {
    if (state.step === 'publisher' && !state.publisherId) {
      setPublisherError('Please select a publisher');
      return;
    }

    if (state.step === 'content-type') {
      if (!state.contentType) {
        setCustomTypeError('Please select a content type');
        return;
      }
      if (state.contentType === 'custom' && !validateCustomContentType(state.customContentType)) {
        return;
      }
    }

    if (state.step === 'files' && state.files.length === 0) {
      setFileError('Please select at least one file');
      return;
    }

    dispatch({ type: 'NEXT_STEP' });
  };

  const handleBack = () => {
    dispatch({ type: 'PREV_STEP' });
  };

  const handleUpload = async () => {
    if (!token || !state.publisherId) return;

    dispatch({ type: 'START_UPLOAD' });

    try {
      const results: UploadResult[] = [];

      if (state.contentType === 'books') {
        // Use existing book upload endpoint with publisher override
        for (const file of state.files) {
          try {
            await uploadNewBookArchive(file, token, tokenType || 'Bearer', undefined, {
              publisherId: state.publisherId!,
            });
            results.push({
              filename: file.name,
              success: true,
              path: `publishers/${selectedPublisher?.name}/books/${file.name}`,
            });
          } catch (error) {
            results.push({
              filename: file.name,
              success: false,
              error: deriveErrorMessage(error),
            });
          }
        }
      } else {
        // For other content types, use asset upload endpoint (Story 9.4)
        const assetType = state.contentType === 'custom'
          ? state.customContentType.toLowerCase()
          : state.contentType!;

        for (const file of state.files) {
          try {
            const result = await uploadPublisherAsset(
              state.publisherId,
              assetType,
              file,
              token,
              tokenType || 'Bearer'
            );
            results.push({
              filename: file.name,
              success: true,
              path: result.path,
            });
          } catch (error) {
            results.push({
              filename: file.name,
              success: false,
              error: deriveErrorMessage(error),
            });
          }
        }
      }

      dispatch({ type: 'UPLOAD_SUCCESS', results });
      onSuccess();

      // Auto-close if all successful
      if (results.every(r => r.success)) {
        setTimeout(() => {
          onClose();
        }, 2000);
      }
    } catch (error) {
      dispatch({ type: 'UPLOAD_ERROR', error: deriveErrorMessage(error) });
    }
  };

  const handleClose = () => {
    if (state.step !== 'uploading') {
      onClose();
    }
  };

  const getStepIndex = (): number => {
    const steps: UploadStep[] = initialPublisherId
      ? ['content-type', 'files']
      : ['publisher', 'content-type', 'files'];
    return steps.indexOf(state.step);
  };

  const canGoNext = (): boolean => {
    if (state.step === 'publisher') return !!state.publisherId;
    if (state.step === 'content-type') {
      if (!state.contentType) return false;
      if (state.contentType === 'custom') {
        return !!state.customContentType.trim() && !customTypeError;
      }
      return true;
    }
    if (state.step === 'files') return state.files.length > 0 && !fileError;
    return false;
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Upload Publisher Content</DialogTitle>
      <DialogContent>
        {!['uploading', 'success', 'error'].includes(state.step) && (
          <Stepper activeStep={getStepIndex()} sx={{ mb: 4, mt: 2 }}>
            {!initialPublisherId && <Step><StepLabel>Select Publisher</StepLabel></Step>}
            <Step><StepLabel>Content Type</StepLabel></Step>
            <Step><StepLabel>Select Files</StepLabel></Step>
          </Stepper>
        )}

        {/* Step 1: Publisher Selection */}
        {state.step === 'publisher' && (
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Select the publisher for this upload.
            </Typography>
            <Autocomplete
              options={publishers}
              getOptionLabel={(option) => option.display_name || option.name}
              loading={loadingPublishers}
              value={selectedPublisher || null}
              onChange={(_, value) => {
                if (value) {
                  dispatch({ type: 'SET_PUBLISHER', publisherId: value.id });
                  setPublisherError('');
                }
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Publisher"
                  required
                  error={!!publisherError}
                  helperText={publisherError}
                />
              )}
              fullWidth
            />
          </Box>
        )}

        {/* Step 2: Content Type Selection */}
        {state.step === 'content-type' && (
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Select the type of content you're uploading.
            </Typography>
            <FormControl component="fieldset" error={!!customTypeError} fullWidth>
              <RadioGroup
                value={state.contentType || ''}
                onChange={(e) => {
                  dispatch({ type: 'SET_CONTENT_TYPE', contentType: e.target.value });
                  setCustomTypeError('');
                }}
              >
                {PREDEFINED_TYPES.map((type) => (
                  <FormControlLabel
                    key={type}
                    value={type}
                    control={<Radio />}
                    label={
                      <Box>
                        <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                          {type}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {CONTENT_TYPE_RULES[type].acceptedFormats} (max {CONTENT_TYPE_RULES[type].maxSize / (1024 * 1024)}MB)
                        </Typography>
                      </Box>
                    }
                  />
                ))}
                <FormControlLabel
                  value="custom"
                  control={<Radio />}
                  label="Add New Type"
                />
              </RadioGroup>
              {state.contentType === 'custom' && (
                <TextField
                  label="Custom Content Type"
                  value={state.customContentType}
                  onChange={(e) => {
                    dispatch({ type: 'SET_CUSTOM_CONTENT_TYPE', customContentType: e.target.value });
                    validateCustomContentType(e.target.value);
                  }}
                  error={!!customTypeError}
                  helperText={customTypeError || 'Use lowercase letters, numbers, hyphens, or underscores'}
                  fullWidth
                  sx={{ mt: 2 }}
                />
              )}
              {customTypeError && state.contentType !== 'custom' && (
                <FormHelperText>{customTypeError}</FormHelperText>
              )}
            </FormControl>
          </Box>
        )}

        {/* Step 3: File Selection */}
        {state.step === 'files' && (
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Select files to upload.
            </Typography>
            <Box
              sx={{
                border: '2px dashed',
                borderColor: fileError ? 'error.main' : 'divider',
                borderRadius: 2,
                p: 4,
                textAlign: 'center',
                bgcolor: 'background.default',
                mb: 2,
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '200px',
                '&:hover': {
                  borderColor: 'primary.main',
                  bgcolor: 'action.hover',
                },
              }}
              component="label"
            >
              <CloudUploadIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                {state.files.length > 0
                  ? `${state.files.length} file${state.files.length > 1 ? 's' : ''} selected`
                  : 'Click to select files'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                or drag and drop here
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                Accepted: {getContentTypeRules().acceptedFormats}
              </Typography>
              <input
                type="file"
                accept={getContentTypeRules().accept}
                multiple={getContentTypeRules().multiple}
                hidden
                onChange={handleFileChange}
                data-testid="publisher-upload-file-input"
              />
            </Box>

            {state.files.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                  Selected files:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {state.files.map((file, index) => (
                    <Chip key={index} label={file.name} size="small" />
                  ))}
                </Box>
              </Box>
            )}

            {fileError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {fileError}
              </Alert>
            )}
          </Box>
        )}

        {/* Uploading State */}
        {state.step === 'uploading' && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="h6" gutterBottom>
              Uploading files...
            </Typography>
            <LinearProgress sx={{ mt: 2 }} />
          </Box>
        )}

        {/* Success State */}
        {state.step === 'success' && (
          <Box>
            <Alert severity="success" sx={{ mb: 3 }}>
              Upload completed successfully!
            </Alert>
            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              Upload Results:
            </Typography>
            <Box>
              {state.uploadResults.map((result, index) => (
                <Box
                  key={index}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    p: 2,
                    mb: 1,
                    bgcolor: result.success ? 'success.light' : 'error.light',
                    borderRadius: 1,
                  }}
                >
                  {result.success ? (
                    <CheckCircleIcon color="success" sx={{ mr: 2 }} />
                  ) : (
                    <ErrorIcon color="error" sx={{ mr: 2 }} />
                  )}
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {result.filename}
                    </Typography>
                    {result.success ? (
                      <Typography variant="caption" color="text.secondary">
                        {selectedPublisher?.display_name || selectedPublisher?.name} / {state.contentType} / {result.path}
                      </Typography>
                    ) : (
                      <Typography variant="caption" color="error">
                        {result.error}
                      </Typography>
                    )}
                  </Box>
                </Box>
              ))}
            </Box>
          </Box>
        )}

        {/* Error State */}
        {state.step === 'error' && state.error && (
          <Alert severity="error">{state.error}</Alert>
        )}
      </DialogContent>
      <DialogActions>
        {!['uploading', 'success'].includes(state.step) && (
          <>
            <Button onClick={handleClose}>Cancel</Button>
            {state.step !== 'publisher' && !initialPublisherId && (
              <Button onClick={handleBack}>Back</Button>
            )}
            {state.step !== 'files' ? (
              <Button
                onClick={handleNext}
                variant="contained"
                disabled={!canGoNext()}
              >
                Next
              </Button>
            ) : (
              <Button
                onClick={handleUpload}
                variant="contained"
                disabled={!canGoNext()}
              >
                Upload
              </Button>
            )}
          </>
        )}
        {state.step === 'success' && (
          <Button onClick={handleClose} variant="contained">
            Close
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default PublisherUploadDialog;
