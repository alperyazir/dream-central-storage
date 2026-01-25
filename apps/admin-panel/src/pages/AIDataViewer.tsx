import { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import PendingIcon from '@mui/icons-material/Pending';
import RefreshIcon from '@mui/icons-material/Refresh';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';
import StopIcon from '@mui/icons-material/Stop';

import {
  AIMetadata,
  BookWithProcessingStatus,
  getBooksWithProcessingStatus,
  getAIMetadata,
  getAIModules,
  getAIModuleDetail,
  getAIVocabulary,
  getVocabularyAudioUrl,
  ModuleDetail,
  ModuleSummary,
  VocabularyWord,
  VocabularyResponse,
} from '../lib/processing';
import { useAuthStore } from '../stores/auth';

import '../styles/page.css';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ py: 2 }}>{children}</Box>}
    </div>
  );
}

const AIDataViewerPage = () => {
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Book selection
  const [books, setBooks] = useState<BookWithProcessingStatus[]>([]);
  const [selectedBook, setSelectedBook] = useState<BookWithProcessingStatus | null>(null);
  const [booksLoading, setBooksLoading] = useState(true);

  // Tab state
  const [tabIndex, setTabIndex] = useState(0);

  // Data state
  const [metadata, setMetadata] = useState<AIMetadata | null>(null);
  const [modules, setModules] = useState<ModuleSummary[]>([]);
  const [expandedModule, setExpandedModule] = useState<number | null>(null);
  const [moduleDetails, setModuleDetails] = useState<Record<number, ModuleDetail>>({});
  const [vocabulary, setVocabulary] = useState<VocabularyWord[]>([]);
  const [totalVocabulary, setTotalVocabulary] = useState(0);
  const [vocabLanguage, setVocabLanguage] = useState<string>('en');
  const [vocabTranslationLang, setVocabTranslationLang] = useState<string>('tr');

  // Audio playback state
  const [playingWord, setPlayingWord] = useState<string | null>(null);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);

  // Load books on mount
  useEffect(() => {
    const loadBooks = async () => {
      if (!token) return;
      setBooksLoading(true);
      try {
        const response = await getBooksWithProcessingStatus(token, tokenType ?? undefined, {
          status: 'completed',
          page_size: 100,
        });
        setBooks(response.books);
      } catch {
        setError('Failed to load books');
      } finally {
        setBooksLoading(false);
      }
    };
    loadBooks();
  }, [token, tokenType]);

  // Load data when book is selected
  const loadBookData = useCallback(async () => {
    if (!token || !selectedBook) return;

    setLoading(true);
    setError(null);
    setMetadata(null);
    setModules([]);
    setVocabulary([]);
    setModuleDetails({});
    setExpandedModule(null);

    try {
      // Load metadata
      const metadataData = await getAIMetadata(selectedBook.book_id, token, tokenType ?? undefined);
      setMetadata(metadataData);

      // Load modules
      const modulesData = await getAIModules(selectedBook.book_id, token, tokenType ?? undefined);
      setModules(modulesData.modules);

      // Load vocabulary
      const vocabData = await getAIVocabulary(selectedBook.book_id, token, tokenType ?? undefined, {
        page_size: 100,
      });
      setVocabulary(vocabData.words);
      setTotalVocabulary(vocabData.total_words);
      setVocabLanguage(vocabData.language || 'en');
      setVocabTranslationLang(vocabData.translation_language || 'tr');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load AI data');
    } finally {
      setLoading(false);
    }
  }, [token, tokenType, selectedBook]);

  useEffect(() => {
    if (selectedBook) {
      loadBookData();
    }
  }, [selectedBook, loadBookData]);

  // Load module details when expanded
  const handleExpandModule = async (moduleId: number) => {
    if (expandedModule === moduleId) {
      setExpandedModule(null);
      return;
    }

    setExpandedModule(moduleId);

    if (!token || !selectedBook || moduleDetails[moduleId]) return;

    try {
      const detail = await getAIModuleDetail(
        selectedBook.book_id,
        moduleId,
        token,
        tokenType ?? undefined
      );
      setModuleDetails((prev) => ({ ...prev, [moduleId]: detail }));
    } catch (err) {
      console.error('Failed to load module detail:', err);
    }
  };

  // Extract filename from audio path (e.g., "audio/vocabulary/en/word_1.mp3" -> "word_1")
  const extractAudioFilename = (audioPath: string | null | undefined): string | null => {
    if (!audioPath) return null;
    const match = audioPath.match(/\/([^/]+)\.mp3$/);
    return match ? match[1] : null;
  };

  // Audio playback handler
  const handlePlayAudio = async (audioPath: string | null | undefined, wordKey: string) => {
    if (!token || !selectedBook || !audioPath) return;

    const filename = extractAudioFilename(audioPath);
    if (!filename) {
      console.error('Could not extract filename from audio path:', audioPath);
      return;
    }

    // Extract language from path (e.g., "audio/vocabulary/en/word_1.mp3" -> "en")
    const langMatch = audioPath.match(/\/vocabulary\/(\w+)\//);
    const lang = langMatch ? langMatch[1] : 'en';

    // If same audio is playing, stop it
    if (playingWord === wordKey) {
      if (audioElement) {
        audioElement.pause();
        audioElement.currentTime = 0;
      }
      setPlayingWord(null);
      return;
    }

    // Stop any currently playing audio
    if (audioElement) {
      audioElement.pause();
    }

    try {
      // Get presigned URL for audio
      const response = await getVocabularyAudioUrl(
        selectedBook.book_id,
        lang,
        filename,
        token,
        tokenType ?? undefined
      );

      // Create and play audio
      const audio = new Audio(response.url);
      audio.onended = () => {
        setPlayingWord(null);
      };
      audio.onerror = () => {
        console.error('Failed to play audio');
        setPlayingWord(null);
      };
      await audio.play();
      setAudioElement(audio);
      setPlayingWord(wordKey);
    } catch (err) {
      console.error('Failed to get audio URL:', err);
    }
  };

  const getStageIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon color="success" fontSize="small" />;
      case 'failed':
        return <ErrorIcon color="error" fontSize="small" />;
      default:
        return <PendingIcon color="disabled" fontSize="small" />;
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <Box className="page">
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1">
          AI Data Viewer
        </Typography>
        {selectedBook && (
          <IconButton onClick={loadBookData} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        )}
      </Stack>

      {/* Book Selector */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Autocomplete
          options={books}
          loading={booksLoading}
          getOptionLabel={(option) => `${option.book_title || option.book_name} (${option.publisher_name})`}
          value={selectedBook}
          onChange={(_, newValue) => setSelectedBook(newValue)}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Select a processed book"
              placeholder="Search books..."
              InputProps={{
                ...params.InputProps,
                endAdornment: (
                  <>
                    {booksLoading ? <CircularProgress size={20} /> : null}
                    {params.InputProps.endAdornment}
                  </>
                ),
              }}
            />
          )}
          renderOption={(props, option) => (
            <li {...props} key={option.book_id}>
              <Stack>
                <Typography variant="body1">{option.book_title || option.book_name}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {option.publisher_name} - {option.book_name}
                </Typography>
              </Stack>
            </li>
          )}
        />
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {!loading && selectedBook && metadata && (
        <>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={tabIndex} onChange={(_, v) => setTabIndex(v)}>
              <Tab label="Metadata" />
              <Tab label={`Modules (${modules.length})`} />
              <Tab label={`Vocabulary (${totalVocabulary})`} />
            </Tabs>
          </Box>

          {/* Metadata Tab */}
          <TabPanel value={tabIndex} index={0}>
            <Stack spacing={3}>
              {/* Overview Card */}
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Processing Overview
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  <Stack direction="row" spacing={4} flexWrap="wrap">
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Status
                      </Typography>
                      <Typography>
                        <Chip
                          label={metadata.processing_status}
                          color={metadata.processing_status === 'completed' ? 'success' : 'default'}
                          size="small"
                        />
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Total Pages
                      </Typography>
                      <Typography variant="h6">{metadata.total_pages}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Modules
                      </Typography>
                      <Typography variant="h6">{metadata.total_modules}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Vocabulary
                      </Typography>
                      <Typography variant="h6">{metadata.total_vocabulary}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Audio Files
                      </Typography>
                      <Typography variant="h6">{metadata.total_audio_files}</Typography>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>

              {/* Stages Card */}
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Processing Stages
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Stage</TableCell>
                          <TableCell>Status</TableCell>
                          <TableCell>Completed At</TableCell>
                          <TableCell>Error</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {Object.entries(metadata.stages).map(([stage, result]) => (
                          <TableRow key={stage}>
                            <TableCell>
                              <Stack direction="row" spacing={1} alignItems="center">
                                {getStageIcon(result.status)}
                                <span>{stage.replace('_', ' ')}</span>
                              </Stack>
                            </TableCell>
                            <TableCell>{result.status}</TableCell>
                            <TableCell>{formatDate(result.completed_at)}</TableCell>
                            <TableCell>
                              {result.error_message && (
                                <Typography variant="body2" color="error">
                                  {result.error_message}
                                </Typography>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>

              {/* Languages & Difficulty */}
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Content Analysis
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  <Stack direction="row" spacing={4}>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Primary Language
                      </Typography>
                      <Typography>{metadata.primary_language || '-'}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Languages
                      </Typography>
                      <Stack direction="row" spacing={0.5}>
                        {metadata.languages.map((lang) => (
                          <Chip key={lang} label={lang} size="small" />
                        ))}
                      </Stack>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Difficulty Range
                      </Typography>
                      <Stack direction="row" spacing={0.5}>
                        {metadata.difficulty_range.map((diff) => (
                          <Chip key={diff} label={diff} size="small" color="primary" variant="outlined" />
                        ))}
                      </Stack>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>
            </Stack>
          </TabPanel>

          {/* Modules Tab */}
          <TabPanel value={tabIndex} index={1}>
            <List>
              {modules.map((module) => (
                <Paper key={module.module_id} sx={{ mb: 1 }}>
                  <ListItemButton onClick={() => handleExpandModule(module.module_id)}>
                    <ListItemText
                      primary={`${module.module_id}. ${module.title}`}
                      secondary={`Pages: ${module.pages.join(', ')} | Words: ${module.word_count}`}
                    />
                    {expandedModule === module.module_id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                  </ListItemButton>
                  <Collapse in={expandedModule === module.module_id}>
                    {moduleDetails[module.module_id] ? (
                      <Box sx={{ p: 2, bgcolor: 'background.default' }}>
                        <Stack spacing={2}>
                          <Box>
                            <Typography variant="subtitle2" color="text.secondary">
                              Topics
                            </Typography>
                            <Stack direction="row" spacing={0.5} flexWrap="wrap" sx={{ mt: 0.5 }}>
                              {moduleDetails[module.module_id].topics.map((topic, i) => (
                                <Chip key={i} label={topic} size="small" />
                              ))}
                            </Stack>
                          </Box>
                          <Box>
                            <Typography variant="subtitle2" color="text.secondary">
                              Language / Difficulty
                            </Typography>
                            <Typography>
                              {moduleDetails[module.module_id].language || '-'} /{' '}
                              {moduleDetails[module.module_id].difficulty || '-'}
                            </Typography>
                          </Box>
                          <Box>
                            <Typography variant="subtitle2" color="text.secondary">
                              Text Preview
                            </Typography>
                            <Paper
                              variant="outlined"
                              sx={{
                                p: 1,
                                maxHeight: 200,
                                overflow: 'auto',
                                bgcolor: 'grey.900',
                              }}
                            >
                              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                                {moduleDetails[module.module_id].text.substring(0, 2000)}
                                {moduleDetails[module.module_id].text.length > 2000 && '...'}
                              </Typography>
                            </Paper>
                          </Box>
                        </Stack>
                      </Box>
                    ) : (
                      <Box sx={{ p: 2, textAlign: 'center' }}>
                        <CircularProgress size={24} />
                      </Box>
                    )}
                  </Collapse>
                </Paper>
              ))}
              {modules.length === 0 && (
                <ListItem>
                  <ListItemText primary="No modules found" />
                </ListItem>
              )}
            </List>
          </TabPanel>

          {/* Vocabulary Tab */}
          <TabPanel value={tabIndex} index={2}>
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Word</TableCell>
                    <TableCell>Translation</TableCell>
                    <TableCell>Module</TableCell>
                    <TableCell>Audio</TableCell>
                    <TableCell>Part of Speech</TableCell>
                    <TableCell>Level</TableCell>
                    <TableCell>Definition</TableCell>
                    <TableCell>Example</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {vocabulary.map((word) => (
                    <TableRow key={word.id}>
                      <TableCell>
                        <Typography fontWeight="bold">{word.word}</Typography>
                      </TableCell>
                      <TableCell>{word.translation || '-'}</TableCell>
                      <TableCell>
                        {word.module_title ? (
                          <Chip
                            label={word.module_title}
                            size="small"
                            variant="outlined"
                            color="info"
                            title={`Module ${word.module_id}`}
                          />
                        ) : word.module_id ? (
                          <Chip
                            label={`Module ${word.module_id}`}
                            size="small"
                            variant="outlined"
                          />
                        ) : '-'}
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={0.5}>
                          {/* Play word audio (original language) */}
                          {word.audio?.word && (
                            <IconButton
                              size="small"
                              onClick={() => handlePlayAudio(word.audio?.word, `word:${word.id}`)}
                              color={playingWord === `word:${word.id}` ? 'primary' : 'default'}
                              title={`Play "${word.word}"`}
                            >
                              {playingWord === `word:${word.id}` ? (
                                <StopIcon fontSize="small" />
                              ) : (
                                <VolumeUpIcon fontSize="small" />
                              )}
                            </IconButton>
                          )}
                          {/* Play translation audio */}
                          {word.audio?.translation && word.translation && (
                            <IconButton
                              size="small"
                              onClick={() => handlePlayAudio(word.audio?.translation, `translation:${word.id}`)}
                              color={playingWord === `translation:${word.id}` ? 'primary' : 'default'}
                              title={`Play "${word.translation}"`}
                              sx={{ color: 'secondary.main' }}
                            >
                              {playingWord === `translation:${word.id}` ? (
                                <StopIcon fontSize="small" />
                              ) : (
                                <VolumeUpIcon fontSize="small" />
                              )}
                            </IconButton>
                          )}
                          {/* Show dash if no audio */}
                          {!word.audio?.word && !word.audio?.translation && '-'}
                        </Stack>
                      </TableCell>
                      <TableCell>
                        {word.part_of_speech && (
                          <Chip label={word.part_of_speech} size="small" variant="outlined" />
                        )}
                      </TableCell>
                      <TableCell>
                        {word.level && <Chip label={word.level} size="small" color="primary" />}
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ maxWidth: 200 }}>
                          {word.definition || '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ maxWidth: 250, fontStyle: 'italic' }}>
                          {word.example || '-'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                  {vocabulary.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={8} align="center">
                        No vocabulary found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            {totalVocabulary > 100 && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Showing first 100 of {totalVocabulary} words
              </Typography>
            )}
          </TabPanel>
        </>
      )}

      {!loading && !selectedBook && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">
            Select a processed book to view its AI-generated data
          </Typography>
        </Paper>
      )}
    </Box>
  );
};

export default AIDataViewerPage;
