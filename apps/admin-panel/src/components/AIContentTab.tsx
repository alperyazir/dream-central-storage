import { useCallback, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  IconButton,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import DeleteIcon from '@mui/icons-material/Delete';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';
import StopIcon from '@mui/icons-material/Stop';
import AudiotrackIcon from '@mui/icons-material/Audiotrack';
import MenuBookIcon from '@mui/icons-material/MenuBook';

import {
  ManifestRead,
  AIContentRead,
  getAIContent,
  deleteAIContent,
  getAIContentAudioUrl,
} from '../lib/aiContent';
import { buildAuthHeaders } from '../lib/http';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface AIContentTabProps {
  bookId: number;
  manifests: ManifestRead[];
  token: string;
  tokenType: string;
  onDeleted: (contentId: string) => void;
}

// ---------------------------------------------------------------------------
// Typed item shapes
// ---------------------------------------------------------------------------

interface AudioData {
  audio_base64: string;
  duration_seconds?: number;
  word_timestamps?: Array<{ word: string; start: number; end: number }>;
}

interface ContentItem {
  item_id?: string;
  correct_sentence?: string;
  sentence?: string;
  text?: string;
  question?: string;
  prompt?: string;
  words?: string[];
  word_count?: number;
  audio_url?: string;
  audio_status?: string;
  audio_data?: AudioData;
  difficulty?: string;
  answer?: string;
  correct_answer?: string | number;
  blank?: string;
  options?: string[];
  explanation?: string;
  // Word builder / vocabulary
  word?: string;
  translation?: string;
  definition?: string;
  // Matching
  pairs?: Array<{ term: string; match: string }>;
}

// ---------------------------------------------------------------------------
// Category grouping
// ---------------------------------------------------------------------------

interface CategoryGroup {
  label: string;
  icon: string;
  color: 'primary' | 'info' | 'success' | 'warning' | 'secondary' | 'default';
  activities: ManifestRead[];
  resources: ManifestRead[];
}

const RESOURCE_TYPES = new Set(['passage_audio', 'reading_passage', 'passage audio', 'reading passage']);

const categorize = (type: string): string => {
  const t = type.toLowerCase().replace(/[\s_-]/g, '');
  if (t.includes('mix')) return 'mix';
  if (t.includes('listening')) return 'listening';
  if (t.includes('writing')) return 'writing';
  if (t.includes('vocab') || t.includes('word') || t.includes('matching')) return 'vocabulary';
  if (t.includes('reading') || t.includes('passage')) return 'resources';
  if (t.includes('quiz') || t.includes('mcq')) return 'quiz';
  return 'other';
};

const CATEGORY_META: Record<string, { label: string; icon: string; color: CategoryGroup['color'] }> = {
  mix: { label: 'Mix Mode', icon: '🎯', color: 'primary' },
  listening: { label: 'Listening', icon: '🎧', color: 'info' },
  writing: { label: 'Writing', icon: '✍️', color: 'warning' },
  vocabulary: { label: 'Vocabulary', icon: '📚', color: 'success' },
  quiz: { label: 'Quiz', icon: '❓', color: 'primary' },
  resources: { label: 'Resources', icon: '📎', color: 'secondary' },
  other: { label: 'Other', icon: '📄', color: 'default' },
};

const groupManifests = (manifests: ManifestRead[]): CategoryGroup[] => {
  const groups: Record<string, CategoryGroup> = {};

  for (const m of manifests) {
    const isResource = RESOURCE_TYPES.has(m.activity_type.toLowerCase());
    const cat = isResource ? 'resources' : categorize(m.activity_type);
    if (!groups[cat]) {
      const meta = CATEGORY_META[cat] ?? CATEGORY_META.other;
      groups[cat] = { ...meta, activities: [], resources: [] };
    }
    if (isResource) {
      groups[cat].resources.push(m);
    } else {
      groups[cat].activities.push(m);
    }
  }

  // If there are standalone resources but also a mix mode, attach resources to mix
  if (groups.resources && groups.mix) {
    groups.mix.resources.push(...groups.resources.resources, ...groups.resources.activities);
    delete groups.resources;
  }

  // Order: mix first, then listening, writing, vocabulary, quiz, resources, other
  const order = ['mix', 'listening', 'writing', 'vocabulary', 'quiz', 'resources', 'other'];
  return order.filter((k) => groups[k]).map((k) => groups[k]);
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const difficultyColor = (d: string | null): 'success' | 'warning' | 'error' | 'default' => {
  if (!d) return 'default';
  switch (d.toLowerCase()) {
    case 'easy':
    case 'beginner':
      return 'success';
    case 'medium':
    case 'intermediate':
      return 'warning';
    case 'hard':
    case 'advanced':
      return 'error';
    default:
      return 'default';
  }
};

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString();
};

const prettyType = (type: string) =>
  type
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());

// ---------------------------------------------------------------------------
// Content renderers
// ---------------------------------------------------------------------------

interface ItemRenderProps {
  items: ContentItem[];
  playingAudio: string | null;
  onPlayBase64: (key: string, base64: string) => void;
  onStop: () => void;
  contentId: string;
}

const PlayButton = ({
  audioKey,
  playing,
  onPlay,
  onStop,
}: {
  audioKey: string;
  playing: string | null;
  onPlay: () => void;
  onStop: () => void;
}) => {
  const isPlaying = playing === audioKey;
  return (
    <IconButton
      size="small"
      onClick={(e) => {
        e.stopPropagation();
        isPlaying ? onStop() : onPlay();
      }}
      color={isPlaying ? 'primary' : 'default'}
      title={isPlaying ? 'Stop' : 'Play'}
      sx={{ ml: 'auto' }}
    >
      {isPlaying ? <StopIcon fontSize="small" /> : <VolumeUpIcon fontSize="small" />}
    </IconButton>
  );
};

/** Sentence builder / listening sentence */
const SentenceItems = ({ items, playingAudio, onPlayBase64, onStop, contentId }: ItemRenderProps) => (
  <Stack spacing={1}>
    {items.map((item, i) => {
      const audioKey = `${contentId}:item:${i}`;
      const hasAudio = !!item.audio_data?.audio_base64;
      return (
        <Box
          key={item.item_id ?? i}
          sx={{ p: 1.5, borderRadius: 1, bgcolor: 'action.hover', display: 'flex', alignItems: 'flex-start', gap: 1 }}
        >
          <Typography variant="body2" color="text.secondary" sx={{ minWidth: 24, pt: 0.25 }}>
            {i + 1}.
          </Typography>
          <Box sx={{ flex: 1 }}>
            <Typography variant="body1">
              {item.correct_sentence ?? item.sentence ?? item.text ?? ''}
            </Typography>
            {Array.isArray(item.words) && item.words.length > 0 && (
              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 0.75 }}>
                {item.words.map((w, j) => (
                  <Chip key={j} label={w} size="small" variant="outlined" sx={{ fontSize: '0.75rem' }} />
                ))}
              </Stack>
            )}
            {item.audio_data?.duration_seconds != null && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                {item.audio_data.duration_seconds.toFixed(1)}s
              </Typography>
            )}
          </Box>
          {item.difficulty && (
            <Chip label={item.difficulty} size="small" color={difficultyColor(item.difficulty)} variant="outlined" />
          )}
          {hasAudio && (
            <PlayButton
              audioKey={audioKey}
              playing={playingAudio}
              onPlay={() => onPlayBase64(audioKey, item.audio_data!.audio_base64)}
              onStop={onStop}
            />
          )}
        </Box>
      );
    })}
  </Stack>
);

/** Fill-in-the-blank */
const FillBlankItems = ({ items, playingAudio, onPlayBase64, onStop, contentId }: ItemRenderProps) => (
  <Stack spacing={1}>
    {items.map((item, i) => {
      const audioKey = `${contentId}:item:${i}`;
      const hasAudio = !!item.audio_data?.audio_base64;
      return (
        <Box
          key={item.item_id ?? i}
          sx={{ p: 1.5, borderRadius: 1, bgcolor: 'action.hover', display: 'flex', alignItems: 'flex-start', gap: 1 }}
        >
          <Typography variant="body2" color="text.secondary" sx={{ minWidth: 24, pt: 0.25 }}>
            {i + 1}.
          </Typography>
          <Box sx={{ flex: 1 }}>
            <Typography variant="body1">
              {item.sentence ?? item.text ?? item.correct_sentence ?? ''}
            </Typography>
            {item.answer != null && (
              <Chip label={`Answer: ${String(item.answer)}`} size="small" color="success" variant="outlined" sx={{ mt: 0.5 }} />
            )}
            {Array.isArray(item.options) && item.options.length > 0 && (
              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
                {item.options.map((opt, j) => (
                  <Chip
                    key={j}
                    label={opt}
                    size="small"
                    color={opt === item.answer ? 'success' : 'default'}
                    variant={opt === item.answer ? 'filled' : 'outlined'}
                    sx={{ fontSize: '0.75rem' }}
                  />
                ))}
              </Stack>
            )}
          </Box>
          {hasAudio && (
            <PlayButton
              audioKey={audioKey}
              playing={playingAudio}
              onPlay={() => onPlayBase64(audioKey, item.audio_data!.audio_base64)}
              onStop={onStop}
            />
          )}
        </Box>
      );
    })}
  </Stack>
);

/** MCQ questions */
const MCQItems = ({ items, playingAudio, onPlayBase64, onStop, contentId }: ItemRenderProps) => (
  <Stack spacing={1}>
    {items.map((q, i) => {
      const audioKey = `${contentId}:q:${i}`;
      const hasAudio = !!q.audio_data?.audio_base64;
      return (
        <Box
          key={i}
          sx={{ p: 1.5, borderRadius: 1, bgcolor: 'action.hover' }}
        >
          <Stack direction="row" alignItems="flex-start" spacing={1}>
            <Typography variant="body2" color="text.secondary" sx={{ minWidth: 24, pt: 0.25 }}>
              {i + 1}.
            </Typography>
            <Box sx={{ flex: 1 }}>
              <Typography variant="body1" gutterBottom>
                {q.question ?? q.text ?? q.prompt ?? ''}
              </Typography>
              {Array.isArray(q.options) && (
                <Stack spacing={0.25} sx={{ pl: 1 }}>
                  {q.options.map((opt, j) => {
                    const isCorrect =
                      q.correct_answer === opt ||
                      q.correct_answer === j ||
                      q.answer === opt ||
                      Number(q.answer) === j;
                    return (
                      <Typography
                        key={j}
                        variant="body2"
                        sx={{
                          fontWeight: isCorrect ? 700 : 400,
                          color: isCorrect ? 'success.main' : 'text.primary',
                        }}
                      >
                        {String.fromCharCode(65 + j)}) {String(opt)}
                        {isCorrect && ' ✓'}
                      </Typography>
                    );
                  })}
                </Stack>
              )}
              {q.explanation != null && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block', fontStyle: 'italic' }}>
                  {q.explanation}
                </Typography>
              )}
            </Box>
            {hasAudio && (
              <PlayButton
                audioKey={audioKey}
                playing={playingAudio}
                onPlay={() => onPlayBase64(audioKey, q.audio_data!.audio_base64)}
                onStop={onStop}
              />
            )}
          </Stack>
        </Box>
      );
    })}
  </Stack>
);

/** Word builder / vocabulary items */
const WordItems = ({ items, playingAudio, onPlayBase64, onStop, contentId }: ItemRenderProps) => (
  <Stack spacing={1}>
    {items.map((item, i) => {
      const audioKey = `${contentId}:item:${i}`;
      const hasAudio = !!item.audio_data?.audio_base64;
      const label = item.word ?? item.text ?? item.correct_sentence ?? item.sentence ?? '';
      return (
        <Box
          key={item.item_id ?? i}
          sx={{ p: 1.5, borderRadius: 1, bgcolor: 'action.hover', display: 'flex', alignItems: 'center', gap: 1 }}
        >
          <Typography variant="body2" color="text.secondary" sx={{ minWidth: 24 }}>
            {i + 1}.
          </Typography>
          <Typography variant="body1" fontWeight={600} sx={{ minWidth: 120 }}>
            {label}
          </Typography>
          {item.translation && (
            <Typography variant="body2" color="text.secondary">
              {item.translation}
            </Typography>
          )}
          {item.definition && (
            <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>
              — {item.definition}
            </Typography>
          )}
          {/* Matching pairs */}
          {Array.isArray(item.pairs) && (
            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ flex: 1 }}>
              {item.pairs.map((p, j) => (
                <Chip key={j} label={`${p.term} → ${p.match}`} size="small" variant="outlined" />
              ))}
            </Stack>
          )}
          {item.difficulty && (
            <Chip label={item.difficulty} size="small" color={difficultyColor(item.difficulty)} variant="outlined" />
          )}
          {hasAudio && (
            <PlayButton
              audioKey={audioKey}
              playing={playingAudio}
              onPlay={() => onPlayBase64(audioKey, item.audio_data!.audio_base64)}
              onStop={onStop}
            />
          )}
        </Box>
      );
    })}
  </Stack>
);

/** Smart content renderer — picks the right renderer based on data shape */
const ContentRenderer = ({
  content,
  activityType,
  playingAudio,
  onPlayBase64,
  onStop,
  contentId,
}: {
  content: Record<string, unknown>;
  activityType: string;
  playingAudio: string | null;
  onPlayBase64: (key: string, base64: string) => void;
  onStop: () => void;
  contentId: string;
}) => {
  const questions = content.questions as ContentItem[] | undefined;
  const items = content.items as ContentItem[] | undefined;
  const sentences = content.sentences as ContentItem[] | undefined;
  const words = content.words as ContentItem[] | undefined;
  const passage = content.passage as string | undefined;
  const readingText = content.reading_text as string | undefined;

  const mainItems = questions ?? items ?? sentences ?? words ?? [];
  const passageText = passage ?? readingText;
  const t = activityType.toLowerCase();
  const renderProps = { items: mainItems, playingAudio, onPlayBase64, onStop, contentId };

  // Reading passage text
  const passageBlock = passageText ? (
    <Paper variant="outlined" sx={{ p: 2, maxHeight: 200, overflow: 'auto', mb: 1.5 }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
        <MenuBookIcon fontSize="small" color="action" />
        <Typography variant="subtitle2">Reading Passage</Typography>
      </Stack>
      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
        {passageText}
      </Typography>
    </Paper>
  ) : null;

  if (mainItems.length === 0 && !passageText) {
    return (
      <Paper variant="outlined" sx={{ p: 1.5, maxHeight: 300, overflow: 'auto', bgcolor: 'grey.900' }}>
        <Typography component="pre" variant="body2" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.75rem' }}>
          {JSON.stringify(content, null, 2)}
        </Typography>
      </Paper>
    );
  }

  // Pick renderer
  const isQuestions = !!questions || t.includes('mcq') || t.includes('quiz');
  const isFillBlank = t.includes('fill') || t.includes('blank') || mainItems.some((it) => 'blank' in it || ('answer' in it && 'sentence' in it));
  const isWordType = t.includes('word') || t.includes('vocab') || t.includes('matching');
  const isSentence = t.includes('sentence') || mainItems.some((it) => 'correct_sentence' in it || ('words' in it && Array.isArray(it.words)));

  let Renderer: typeof SentenceItems;
  if (isQuestions) Renderer = MCQItems;
  else if (isFillBlank) Renderer = FillBlankItems;
  else if (isWordType) Renderer = WordItems;
  else if (isSentence) Renderer = SentenceItems;
  else Renderer = SentenceItems; // generic fallback

  return (
    <>
      {passageBlock}
      {mainItems.length > 0 && <Renderer {...renderProps} />}
    </>
  );
};

// ---------------------------------------------------------------------------
// Resource card (passage audio, reading passages) — compact inline
// ---------------------------------------------------------------------------

interface ResourceCardProps {
  manifest: ManifestRead;
  playingAudio: string | null;
  onPlayBase64: (key: string, base64: string) => void;
  onPlayStorage: (contentId: string, filename: string) => void;
  onStop: () => void;
  onDelete: (m: ManifestRead) => void;
  detail: AIContentRead | undefined;
  onExpand: (id: string) => void;
  isExpanded: boolean;
  isLoading: boolean;
}

const ResourceCard = ({ manifest: m, playingAudio, onPlayBase64, onPlayStorage, onStop, onDelete, detail, onExpand, isExpanded, isLoading }: ResourceCardProps) => {
  const isPassageAudio = m.activity_type.toLowerCase().includes('audio');

  return (
    <Box sx={{ p: 1.5, borderRadius: 1, border: 1, borderColor: 'divider', bgcolor: 'background.paper' }}>
      <Stack direction="row" alignItems="center" spacing={1}>
        {isPassageAudio ? (
          <AudiotrackIcon fontSize="small" color="action" />
        ) : (
          <MenuBookIcon fontSize="small" color="action" />
        )}
        <Typography variant="body2" sx={{ flex: 1 }}>
          {m.title}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {formatDate(m.created_at)}
        </Typography>
        {m.has_audio && (
          <Chip label="Audio" size="small" color="info" variant="outlined" sx={{ height: 22, fontSize: '0.7rem' }} />
        )}
        <IconButton size="small" onClick={() => onExpand(m.content_id)} sx={{ p: 0.5 }}>
          {isExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
        </IconButton>
        <IconButton size="small" onClick={() => onDelete(m)} color="error" sx={{ p: 0.5 }}>
          <DeleteIcon fontSize="small" />
        </IconButton>
      </Stack>
      <Collapse in={isExpanded}>
        <Box sx={{ mt: 1, pl: 4 }}>
          {isLoading && <CircularProgress size={20} />}
          {detail && (() => {
            const content = detail.content;
            // Try to play passage audio from storage
            const audioFiles: string[] = [];
            const af = content.audio_files ?? content.audio;
            if (Array.isArray(af)) {
              for (const f of af) {
                if (typeof f === 'string') audioFiles.push(f);
                else if (typeof f === 'object' && f !== null && 'filename' in f)
                  audioFiles.push(String((f as Record<string, unknown>).filename));
              }
            }
            // inline base64 audio
            const items = (content.items ?? content.sentences ?? []) as ContentItem[];
            const hasInlineAudio = items.some((it) => !!it.audio_data?.audio_base64);
            // passage text
            const passageText = (content.passage ?? content.reading_text ?? content.text) as string | undefined;

            return (
              <Stack spacing={1}>
                {passageText && (
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', maxHeight: 150, overflow: 'auto' }}>
                    {passageText}
                  </Typography>
                )}
                {audioFiles.map((filename) => {
                  const key = `${m.content_id}:file:${filename}`;
                  return (
                    <Stack key={filename} direction="row" spacing={1} alignItems="center">
                      <PlayButton
                        audioKey={key}
                        playing={playingAudio}
                        onPlay={() => onPlayStorage(m.content_id, filename)}
                        onStop={onStop}
                      />
                      <Typography variant="body2">{filename}</Typography>
                    </Stack>
                  );
                })}
                {hasInlineAudio && items.map((item, i) => {
                  if (!item.audio_data?.audio_base64) return null;
                  const key = `${m.content_id}:item:${i}`;
                  return (
                    <Stack key={i} direction="row" spacing={1} alignItems="center">
                      <PlayButton
                        audioKey={key}
                        playing={playingAudio}
                        onPlay={() => onPlayBase64(key, item.audio_data!.audio_base64)}
                        onStop={onStop}
                      />
                      <Typography variant="body2">
                        {item.text ?? item.sentence ?? `Audio ${i + 1}`}
                        {item.audio_data.duration_seconds != null && ` (${item.audio_data.duration_seconds.toFixed(1)}s)`}
                      </Typography>
                    </Stack>
                  );
                })}
                {!passageText && audioFiles.length === 0 && !hasInlineAudio && (
                  <Typography component="pre" variant="body2" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.7rem', maxHeight: 150, overflow: 'auto' }}>
                    {JSON.stringify(content, null, 2)}
                  </Typography>
                )}
              </Stack>
            );
          })()}
        </Box>
      </Collapse>
    </Box>
  );
};

// ---------------------------------------------------------------------------
// Activity card
// ---------------------------------------------------------------------------

interface ActivityCardProps {
  manifest: ManifestRead;
  isExpanded: boolean;
  isLoading: boolean;
  detail: AIContentRead | undefined;
  playingAudio: string | null;
  onToggle: (id: string) => void;
  onDelete: (m: ManifestRead) => void;
  onPlayBase64: (key: string, base64: string) => void;
  onPlayStorage: (contentId: string, filename: string) => void;
  onStop: () => void;
}

const ActivityCard = ({ manifest: m, isExpanded, isLoading, detail, playingAudio, onToggle, onDelete, onPlayBase64, onPlayStorage, onStop }: ActivityCardProps) => (
  <Box
    sx={{
      border: 1,
      borderColor: 'divider',
      borderRadius: 1,
      overflow: 'hidden',
      bgcolor: 'background.paper',
    }}
  >
    {/* Compact header */}
    <Box
      onClick={() => onToggle(m.content_id)}
      sx={{
        px: 2,
        py: 1.25,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        '&:hover': { bgcolor: 'action.hover' },
      }}
    >
      <Typography variant="body1" sx={{ fontWeight: 600, flex: 1 }}>
        {m.title}
      </Typography>
      {m.difficulty && (
        <Chip label={m.difficulty} size="small" color={difficultyColor(m.difficulty)} variant="outlined" sx={{ height: 22, fontSize: '0.7rem' }} />
      )}
      {m.item_count > 0 && (
        <Chip label={`${m.item_count}`} size="small" variant="outlined" sx={{ height: 22, fontSize: '0.7rem' }} />
      )}
      {m.has_audio && (
        <AudiotrackIcon fontSize="small" color="info" />
      )}
      <IconButton
        size="small"
        onClick={(e) => { e.stopPropagation(); onDelete(m); }}
        color="error"
        sx={{ p: 0.5 }}
      >
        <DeleteIcon fontSize="small" />
      </IconButton>
      {isExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
    </Box>

    {/* Info row */}
    <Box sx={{ px: 2, pb: isExpanded ? 0 : 1 }}>
      <Typography variant="caption" color="text.secondary">
        {prettyType(m.activity_type)}
        {m.created_by && ` · ${m.created_by.slice(0, 8)}`}
        {m.created_at && ` · ${formatDate(m.created_at)}`}
      </Typography>
    </Box>

    {/* Expanded detail */}
    <Collapse in={isExpanded}>
      <Divider />
      <Box sx={{ p: 2 }}>
        {isLoading && (
          <Box sx={{ textAlign: 'center', py: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}
        {detail && (
          <Stack spacing={1.5}>
            <ContentRenderer
              content={detail.content}
              activityType={m.activity_type}
              playingAudio={playingAudio}
              onPlayBase64={onPlayBase64}
              onStop={onStop}
              contentId={m.content_id}
            />

            {/* Storage audio files */}
            {(() => {
              const audioFiles: string[] = [];
              const af = detail.content.audio_files ?? detail.content.audio;
              if (Array.isArray(af)) {
                for (const f of af) {
                  if (typeof f === 'string') audioFiles.push(f);
                  else if (typeof f === 'object' && f !== null && 'filename' in f)
                    audioFiles.push(String((f as Record<string, unknown>).filename));
                }
              }
              if (typeof detail.content.passage_audio === 'string')
                audioFiles.unshift(detail.content.passage_audio as string);

              if (audioFiles.length === 0) return null;
              return (
                <Box>
                  <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ mb: 0.5, display: 'block' }}>
                    Audio Files
                  </Typography>
                  <Stack spacing={0.5}>
                    {audioFiles.map((filename) => {
                      const key = `${m.content_id}:file:${filename}`;
                      return (
                        <Stack key={filename} direction="row" spacing={1} alignItems="center">
                          <PlayButton audioKey={key} playing={playingAudio} onPlay={() => onPlayStorage(m.content_id, filename)} onStop={onStop} />
                          <Typography variant="body2">{filename}</Typography>
                        </Stack>
                      );
                    })}
                  </Stack>
                </Box>
              );
            })()}
          </Stack>
        )}
        {!detail && !isLoading && (
          <Alert severity="warning" variant="outlined">Failed to load content</Alert>
        )}
      </Box>
    </Collapse>
  </Box>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const AIContentTab = ({ bookId, manifests, token, tokenType, onDeleted }: AIContentTabProps) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [contentCache, setContentCache] = useState<Record<string, AIContentRead>>({});
  const [loadingContent, setLoadingContent] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ManifestRead | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [playingAudio, setPlayingAudio] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const groups = useMemo(() => groupManifests(manifests), [manifests]);

  const handleToggle = useCallback(
    async (contentId: string) => {
      if (expandedId === contentId) { setExpandedId(null); return; }
      setExpandedId(contentId);
      if (contentCache[contentId]) return;
      setLoadingContent(contentId);
      try {
        const data = await getAIContent(bookId, contentId, token, tokenType);
        setContentCache((prev) => ({ ...prev, [contentId]: data }));
      } catch (err) {
        console.error('Failed to load AI content:', err);
      } finally {
        setLoadingContent(null);
      }
    },
    [expandedId, contentCache, bookId, token, tokenType]
  );

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteAIContent(bookId, deleteTarget.content_id, token, tokenType);
      setContentCache((prev) => { const n = { ...prev }; delete n[deleteTarget.content_id]; return n; });
      if (expandedId === deleteTarget.content_id) setExpandedId(null);
      onDeleted(deleteTarget.content_id);
      setDeleteTarget(null);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Failed to delete');
    } finally {
      setDeleting(false);
    }
  }, [deleteTarget, bookId, token, tokenType, expandedId, onDeleted]);

  const stopAudio = useCallback(() => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.currentTime = 0; }
    setPlayingAudio(null);
  }, []);

  const playBase64Audio = useCallback(
    (key: string, base64: string) => {
      if (playingAudio === key) { stopAudio(); return; }
      stopAudio();
      const src = base64.startsWith('data:') ? base64 : `data:audio/mpeg;base64,${base64}`;
      const audio = new Audio(src);
      audio.onended = () => setPlayingAudio(null);
      audio.onerror = () => setPlayingAudio(null);
      audio.play();
      audioRef.current = audio;
      setPlayingAudio(key);
    },
    [playingAudio, stopAudio]
  );

  const playStorageAudio = useCallback(
    async (contentId: string, filename: string) => {
      const key = `${contentId}:file:${filename}`;
      if (playingAudio === key) { stopAudio(); return; }
      stopAudio();
      try {
        const url = getAIContentAudioUrl(bookId, contentId, filename);
        const response = await fetch(url, { headers: buildAuthHeaders(token, tokenType) });
        if (!response.ok) throw new Error('Audio fetch failed');
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);
        const audio = new Audio(blobUrl);
        audio.onended = () => { setPlayingAudio(null); URL.revokeObjectURL(blobUrl); };
        audio.onerror = () => { setPlayingAudio(null); URL.revokeObjectURL(blobUrl); };
        await audio.play();
        audioRef.current = audio;
        setPlayingAudio(key);
      } catch (err) {
        console.error('Failed to play storage audio:', err);
        setPlayingAudio(null);
      }
    },
    [playingAudio, stopAudio, bookId, token, tokenType]
  );

  if (manifests.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">No AI content generated for this book</Typography>
      </Paper>
    );
  }

  return (
    <>
      <Stack spacing={3}>
        {groups.map((group) => (
          <Box key={group.label}>
            {/* Category header */}
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.5 }}>
              <Typography variant="body1" sx={{ fontSize: '1.1rem' }}>
                {group.icon}
              </Typography>
              <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 700 }}>
                {group.label}
              </Typography>
              <Chip
                label={group.activities.length + group.resources.length}
                size="small"
                color={group.color}
                sx={{ height: 22, fontSize: '0.75rem' }}
              />
            </Stack>

            {/* Activity cards */}
            <Stack spacing={1}>
              {group.activities.map((m) => (
                <ActivityCard
                  key={m.content_id}
                  manifest={m}
                  isExpanded={expandedId === m.content_id}
                  isLoading={loadingContent === m.content_id}
                  detail={contentCache[m.content_id]}
                  playingAudio={playingAudio}
                  onToggle={handleToggle}
                  onDelete={setDeleteTarget}
                  onPlayBase64={playBase64Audio}
                  onPlayStorage={playStorageAudio}
                  onStop={stopAudio}
                />
              ))}
            </Stack>

            {/* Resources nested under category */}
            {group.resources.length > 0 && (
              <Box sx={{ mt: 1, ml: 2 }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ mb: 0.75, display: 'block', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Resources
                </Typography>
                <Stack spacing={0.75}>
                  {group.resources.map((m) => (
                    <ResourceCard
                      key={m.content_id}
                      manifest={m}
                      playingAudio={playingAudio}
                      onPlayBase64={playBase64Audio}
                      onPlayStorage={playStorageAudio}
                      onStop={stopAudio}
                      onDelete={setDeleteTarget}
                      detail={contentCache[m.content_id]}
                      onExpand={handleToggle}
                      isExpanded={expandedId === m.content_id}
                      isLoading={loadingContent === m.content_id}
                    />
                  ))}
                </Stack>
              </Box>
            )}
          </Box>
        ))}
      </Stack>

      {/* Delete dialog */}
      <Dialog open={!!deleteTarget} onClose={() => !deleting && setDeleteTarget(null)}>
        <DialogTitle>Delete AI Content</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Permanently delete <strong>{deleteTarget?.title}</strong>?
            This removes manifest, content, and all audio files.
          </DialogContentText>
          {deleteError && <Alert severity="error" sx={{ mt: 2 }}>{deleteError}</Alert>}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained" disabled={deleting}>
            {deleting ? <CircularProgress size={20} /> : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default AIContentTab;
