import { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  SelectChangeEvent,
  Slider,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import RefreshIcon from '@mui/icons-material/Refresh';

import {
  GlobalProcessingSettingsUpdate,
  getProcessingSettings,
  updateProcessingSettings,
} from '../lib/processing';
import { useAuthStore } from '../stores/auth';
import { ApiError } from '../lib/api';

import '../styles/page.css';

const LLM_PROVIDERS = [
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'gemini', label: 'Google Gemini' },
];

const TTS_PROVIDERS = [
  { value: 'edge', label: 'Edge TTS (Free)' },
  { value: 'azure', label: 'Azure TTS' },
];

const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'tr', label: 'Turkish' },
  { value: 'de', label: 'German' },
  { value: 'fr', label: 'French' },
  { value: 'es', label: 'Spanish' },
];

const ProcessingSettingsPage = () => {
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType);

  // Settings state
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [autoProcessOnUpload, setAutoProcessOnUpload] = useState(true);
  const [skipExisting, setSkipExisting] = useState(true);
  const [llmPrimary, setLlmPrimary] = useState('deepseek');
  const [llmFallback, setLlmFallback] = useState('gemini');
  const [ttsPrimary, setTtsPrimary] = useState('edge');
  const [ttsFallback, setTtsFallback] = useState('azure');
  const [queueConcurrency, setQueueConcurrency] = useState(3);
  const [vocabMaxWords, setVocabMaxWords] = useState(50);
  const [audioLanguages, setAudioLanguages] = useState('en,tr');
  const [audioConcurrency, setAudioConcurrency] = useState(5);

  const fetchSettings = useCallback(async () => {
    if (!token) return;

    setLoading(true);
    setError(null);

    try {
      const data = await getProcessingSettings(token, tokenType ?? undefined);

      // Update form state
      setAutoProcessOnUpload(data.ai_auto_process_on_upload);
      setSkipExisting(data.ai_auto_process_skip_existing);
      setLlmPrimary(data.llm_primary_provider);
      setLlmFallback(data.llm_fallback_provider);
      setTtsPrimary(data.tts_primary_provider);
      setTtsFallback(data.tts_fallback_provider);
      setQueueConcurrency(data.queue_max_concurrency);
      setVocabMaxWords(data.vocabulary_max_words_per_module);
      setAudioLanguages(data.audio_generation_languages);
      setAudioConcurrency(data.audio_generation_concurrency);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load settings');
      }
    } finally {
      setLoading(false);
    }
  }, [token, tokenType]);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const handleSave = useCallback(async () => {
    if (!token) return;

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const update: GlobalProcessingSettingsUpdate = {
        ai_auto_process_on_upload: autoProcessOnUpload,
        ai_auto_process_skip_existing: skipExisting,
        llm_primary_provider: llmPrimary,
        llm_fallback_provider: llmFallback,
        tts_primary_provider: ttsPrimary,
        tts_fallback_provider: ttsFallback,
        queue_max_concurrency: queueConcurrency,
        vocabulary_max_words_per_module: vocabMaxWords,
        audio_generation_languages: audioLanguages,
        audio_generation_concurrency: audioConcurrency,
      };

      await updateProcessingSettings(update, token, tokenType ?? undefined);
      setSuccess('Settings saved successfully. Note: Changes are temporary and will reset on server restart.');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to save settings');
      }
    } finally {
      setSaving(false);
    }
  }, [
    token,
    tokenType,
    autoProcessOnUpload,
    skipExisting,
    llmPrimary,
    llmFallback,
    ttsPrimary,
    ttsFallback,
    queueConcurrency,
    vocabMaxWords,
    audioLanguages,
    audioConcurrency,
  ]);

  const handleLanguageChange = (event: SelectChangeEvent<string[]>) => {
    const value = event.target.value;
    setAudioLanguages(Array.isArray(value) ? value.join(',') : value);
  };

  if (loading) {
    return (
      <Box className="page" sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box className="page">
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1">
          AI Processing Settings
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={fetchSettings} disabled={loading}>
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </Button>
        </Stack>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Stack spacing={3}>
        {/* Auto-Processing Settings */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Auto-Processing
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Stack spacing={2}>
              <FormControlLabel
                control={
                  <Switch
                    checked={autoProcessOnUpload}
                    onChange={(e) => setAutoProcessOnUpload(e.target.checked)}
                  />
                }
                label="Auto-process books on upload"
              />
              <Typography variant="body2" color="text.secondary" sx={{ ml: 4, mt: -1 }}>
                Automatically trigger AI processing when new books are uploaded.
              </Typography>

              <FormControlLabel
                control={
                  <Switch checked={skipExisting} onChange={(e) => setSkipExisting(e.target.checked)} />
                }
                label="Skip already processed books"
              />
              <Typography variant="body2" color="text.secondary" sx={{ ml: 4, mt: -1 }}>
                Skip processing if the book already has AI data (unless forced).
              </Typography>
            </Stack>
          </CardContent>
        </Card>

        {/* LLM Provider Settings */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              LLM Providers
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Stack direction="row" spacing={3}>
              <FormControl fullWidth>
                <InputLabel>Primary Provider</InputLabel>
                <Select
                  value={llmPrimary}
                  label="Primary Provider"
                  onChange={(e) => setLlmPrimary(e.target.value)}
                >
                  {LLM_PROVIDERS.map((provider) => (
                    <MenuItem key={provider.value} value={provider.value}>
                      {provider.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel>Fallback Provider</InputLabel>
                <Select
                  value={llmFallback}
                  label="Fallback Provider"
                  onChange={(e) => setLlmFallback(e.target.value)}
                >
                  {LLM_PROVIDERS.map((provider) => (
                    <MenuItem key={provider.value} value={provider.value}>
                      {provider.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>
          </CardContent>
        </Card>

        {/* TTS Provider Settings */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              TTS Providers (Audio Generation)
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Stack direction="row" spacing={3}>
              <FormControl fullWidth>
                <InputLabel>Primary Provider</InputLabel>
                <Select
                  value={ttsPrimary}
                  label="Primary Provider"
                  onChange={(e) => setTtsPrimary(e.target.value)}
                >
                  {TTS_PROVIDERS.map((provider) => (
                    <MenuItem key={provider.value} value={provider.value}>
                      {provider.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel>Fallback Provider</InputLabel>
                <Select
                  value={ttsFallback}
                  label="Fallback Provider"
                  onChange={(e) => setTtsFallback(e.target.value)}
                >
                  {TTS_PROVIDERS.map((provider) => (
                    <MenuItem key={provider.value} value={provider.value}>
                      {provider.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>
          </CardContent>
        </Card>

        {/* Vocabulary Extraction Settings */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Vocabulary Extraction
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Box sx={{ px: 2 }}>
              <Typography gutterBottom>Max Words per Module: {vocabMaxWords}</Typography>
              <Slider
                value={vocabMaxWords}
                onChange={(_, value) => setVocabMaxWords(value as number)}
                min={10}
                max={100}
                step={5}
                marks={[
                  { value: 10, label: '10' },
                  { value: 50, label: '50' },
                  { value: 100, label: '100' },
                ]}
                valueLabelDisplay="auto"
              />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Maximum number of vocabulary words to extract per module/chapter.
              </Typography>
            </Box>
          </CardContent>
        </Card>

        {/* Audio Generation Settings */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Audio Generation
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Stack spacing={3}>
              <FormControl fullWidth>
                <InputLabel>Languages</InputLabel>
                <Select
                  multiple
                  value={audioLanguages.split(',').filter(Boolean)}
                  label="Languages"
                  onChange={handleLanguageChange}
                  renderValue={(selected) =>
                    selected
                      .map((v) => LANGUAGE_OPTIONS.find((l) => l.value === v)?.label || v)
                      .join(', ')
                  }
                >
                  {LANGUAGE_OPTIONS.map((lang) => (
                    <MenuItem key={lang.value} value={lang.value}>
                      {lang.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Typography variant="body2" color="text.secondary" sx={{ mt: -2 }}>
                Languages for which to generate audio pronunciations.
              </Typography>

              <TextField
                label="Concurrency"
                type="number"
                value={audioConcurrency}
                onChange={(e) => setAudioConcurrency(parseInt(e.target.value, 10) || 1)}
                inputProps={{ min: 1, max: 20 }}
                helperText="Number of concurrent TTS requests during batch audio generation."
              />
            </Stack>
          </CardContent>
        </Card>

        {/* Queue Settings */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Processing Queue
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <TextField
              label="Max Concurrency"
              type="number"
              value={queueConcurrency}
              onChange={(e) => setQueueConcurrency(parseInt(e.target.value, 10) || 1)}
              inputProps={{ min: 1, max: 10 }}
              helperText="Maximum number of books to process concurrently."
              fullWidth
            />
          </CardContent>
        </Card>
      </Stack>
    </Box>
  );
};

export default ProcessingSettingsPage;
