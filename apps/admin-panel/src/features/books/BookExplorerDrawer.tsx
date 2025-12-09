import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Collapse,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Stack,
  Tooltip,
  Typography
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import FolderIcon from '@mui/icons-material/Folder';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import InsertDriveFileOutlinedIcon from '@mui/icons-material/InsertDriveFileOutlined';
import DownloadForOfflineOutlinedIcon from '@mui/icons-material/DownloadForOfflineOutlined';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';

import type { StorageNode } from '../../lib/storage';
import { downloadBookObject, fetchBookExplorerData } from '../../lib/storage';
import type { BookListRow } from './types';

interface BookExplorerDrawerProps {
  open: boolean;
  onClose: () => void;
  book: BookListRow | null;
  token: string | null;
  tokenType: string;
}

interface ExplorerNode {
  id: string;
  name: string;
  type: 'folder' | 'file';
  size?: number;
  path: string;
  relativePath: string;
  children: ExplorerNode[];
}

interface ExplorerMetadata {
  publisher?: string;
  bookName?: string;
  language?: string;
  category?: string;
  version?: string;
  status?: string;
  createdAt?: string;
  updatedAt?: string;
}

const CONFIG_ALIASES: Record<
  keyof Omit<ExplorerMetadata, 'createdAt' | 'updatedAt'>,
  string[]
> = {
  publisher: ['publisher', 'publisher_name', 'publisherName'],
  bookName: ['book_name', 'book_title', 'bookTitle', 'title'],
  language: ['language', 'lang'],
  category: ['category', 'subject', 'book_category', 'bookCategory'],
  version: ['version', 'book_version', 'bookVersion'],
  status: ['status', 'book_status', 'bookStatus']
};

type PreviewKind = 'none' | 'image' | 'audio' | 'video' | 'unsupported';

type PreviewStatus = 'idle' | 'loading' | 'ready' | 'error';

interface PreviewState {
  kind: PreviewKind;
  status: PreviewStatus;
  url: string | null;
  error: string | null;
}

const IMAGE_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'webp', 'gif']);
const AUDIO_EXTENSIONS = new Set(['mp3', 'wav', 'ogg', 'm4a', 'aac']);
const VIDEO_EXTENSIONS = new Set(['mp4', 'webm', 'mov']);

const inferPreviewKind = (node: ExplorerNode | null): PreviewKind => {
  if (!node || node.type !== 'file') {
    return 'none';
  }

  const relative = node.relativePath || node.name;
  const lastSegment = relative.split('/').pop() ?? relative;
  const extension = lastSegment.split('.').pop()?.toLowerCase() ?? '';

  if (!extension) {
    return 'unsupported';
  }

  if (IMAGE_EXTENSIONS.has(extension)) {
    return 'image';
  }

  if (AUDIO_EXTENSIONS.has(extension)) {
    return 'audio';
  }

  if (VIDEO_EXTENSIONS.has(extension)) {
    return 'video';
  }

  return 'unsupported';
};

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

const formatDateTime = (value?: string) => {
  if (!value) {
    return 'Unknown';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(date);
};

const normalizeChildNode = (node: StorageNode, basePrefix: string): ExplorerNode => {
  const fullPath = node.path;
  const trimmedPrefix = basePrefix.endsWith('/') ? basePrefix : `${basePrefix}/`;
  let relative = fullPath.startsWith(trimmedPrefix) ? fullPath.slice(trimmedPrefix.length) : fullPath;
  relative = relative.replace(/^\/+/, '');
  const isFolder = node.type === 'folder';
  const labelSource = relative || fullPath;
  const name = isFolder
    ? labelSource.replace(/\/$/, '').split('/').filter(Boolean).pop() ?? labelSource
    : labelSource.split('/').filter(Boolean).pop() ?? labelSource;

  const children = (node.children ?? []).map((child) => normalizeChildNode(child, basePrefix));

  return {
    id: fullPath,
    name: name || (isFolder ? 'folder' : 'file'),
    type: node.type,
    size: node.size,
    path: fullPath,
    relativePath: relative,
    children
  };
};

const normalizeRootNode = (root: StorageNode, book: BookListRow): ExplorerNode => {
  const basePrefix = `${book.publisher}/${book.bookName}/`;

  return {
    id: root.path,
    name: book.bookName,
    type: 'folder',
    size: root.size,
    path: root.path,
    relativePath: '',
    children: (root.children ?? []).map((child) => normalizeChildNode(child, basePrefix))
  };
};

const extractConfigField = (config: Record<string, unknown> | null, candidates: string[]) => {
  if (!config) {
    return undefined;
  }

  for (const key of candidates) {
    const value = config[key];
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }

  return undefined;
};

const buildMetadata = (
  config: Record<string, unknown> | null,
  book: BookListRow | null
): ExplorerMetadata => ({
  publisher: extractConfigField(config, CONFIG_ALIASES.publisher) ?? book?.publisher,
  bookName: extractConfigField(config, CONFIG_ALIASES.bookName) ?? book?.bookName,
  language: extractConfigField(config, CONFIG_ALIASES.language) ?? book?.language,
  category: extractConfigField(config, CONFIG_ALIASES.category) ?? book?.category,
  version: extractConfigField(config, CONFIG_ALIASES.version),
  status: (extractConfigField(config, CONFIG_ALIASES.status) ?? book?.status)?.toString(),
  createdAt: book?.createdAt,
  updatedAt: book?.updatedAt
});

interface ExplorerTreeProps {
  root: ExplorerNode | null;
  selectedPath: string | null;
  onSelect: (node: ExplorerNode) => void;
  onDownload: (node: ExplorerNode) => void;
  onCopyPath: (node: ExplorerNode) => void;
}

const ExplorerTree = ({ root, selectedPath, onSelect, onDownload, onCopyPath }: ExplorerTreeProps) => {
  if (!root) {
    return null;
  }

  return (
    <List disablePadding dense>
      {root.children.map((child) => (
        <ExplorerTreeItem
          key={child.id}
          node={child}
          depth={0}
          selectedPath={selectedPath}
          onSelect={onSelect}
          onDownload={onDownload}
          onCopyPath={onCopyPath}
        />
      ))}
    </List>
  );
};

interface ExplorerTreeItemProps {
  node: ExplorerNode;
  depth: number;
  selectedPath: string | null;
  onSelect: (node: ExplorerNode) => void;
  onDownload: (node: ExplorerNode) => void;
  onCopyPath: (node: ExplorerNode) => void;
}

const ExplorerTreeItem = ({
  node,
  depth,
  selectedPath,
  onSelect,
  onDownload,
  onCopyPath
}: ExplorerTreeItemProps) => {
  const [open, setOpen] = useState(depth === 0);
  const isSelected = selectedPath === node.path;

  const handleToggle = () => {
    setOpen((value) => !value);
  };

  if (node.type === 'folder') {
    return (
      <>
        <ListItemButton
          onClick={handleToggle}
          sx={{ pl: (depth + 1) * 2 }}
          aria-expanded={open}
        >
          {open ? <FolderOpenIcon fontSize="small" /> : <FolderIcon fontSize="small" />}
          <ListItemText
            primary={node.name}
            secondary={node.relativePath || (depth === 0 ? '/' : undefined)}
            sx={{ ml: 1 }}
            primaryTypographyProps={{ variant: 'body2' }}
            secondaryTypographyProps={{ variant: 'caption', color: 'text.secondary' }}
          />
          {open ? <Typography variant="caption">Hide</Typography> : <Typography variant="caption">Show</Typography>}
        </ListItemButton>
        <Collapse in={open} timeout="auto" unmountOnExit>
          <List disablePadding dense>
            {node.children.map((child) => (
              <ExplorerTreeItem
                key={child.id}
                node={child}
                depth={depth + 1}
                selectedPath={selectedPath}
                onSelect={onSelect}
                onDownload={onDownload}
                onCopyPath={onCopyPath}
              />
            ))}
          </List>
        </Collapse>
      </>
    );
  }

  return (
    <ListItemButton
      onClick={() => onSelect(node)}
      sx={{ pl: (depth + 1) * 2 }}
      selected={isSelected}
    >
      <InsertDriveFileOutlinedIcon fontSize="small" />
      <ListItemText
        primary={node.name}
        secondary={[node.relativePath || node.name, formatBytes(node.size)].join(' • ')}
        sx={{ ml: 1 }}
        primaryTypographyProps={{ variant: 'body2' }}
        secondaryTypographyProps={{ variant: 'caption', color: 'text.secondary' }}
      />
      {isSelected ? (
        <Stack direction="row" spacing={1} sx={{ ml: 1 }}>
          <Tooltip title="Download file">
            <span>
              <IconButton
                size="small"
                onClick={() => onDownload(node)}
                aria-label={`Download file ${node.name}`}
              >
                <DownloadForOfflineOutlinedIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title="Copy storage path">
            <span>
              <IconButton
                size="small"
                onClick={() => onCopyPath(node)}
                aria-label={`Copy storage path for ${node.name}`}
              >
                <ContentCopyIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>
      ) : null}
    </ListItemButton>
  );
};

const BookExplorerDrawer = ({ open, onClose, book, token, tokenType }: BookExplorerDrawerProps) => {
  const [loading, setLoading] = useState(false);
  const [tree, setTree] = useState<ExplorerNode | null>(null);
  const [metadata, setMetadata] = useState<ExplorerMetadata | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<ExplorerNode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ severity: 'success' | 'error'; message: string } | null>(null);
  const [preview, setPreview] = useState<PreviewState>({
    kind: 'none',
    status: 'idle',
    url: null,
    error: null
  });
  const previewUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (!open) {
      setTree(null);
      setMetadata(null);
      setSelectedPath(null);
      setSelectedNode(null);
      setError(null);
      setMetadataError(null);
      setFeedback(null);
      setLoading(false);
      setPreview({
        kind: 'none',
        status: 'idle',
        url: null,
        error: null
      });
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = null;
      }
      return;
    }

    if (!book || !token) {
      setError('Authentication is required to explore book contents.');
      setMetadata(buildMetadata(null, book));
      setTree(null);
      setLoading(false);
      setSelectedNode(null);
      setPreview({
        kind: 'none',
        status: 'idle',
        url: null,
        error: null
      });
      return;
    }

    let isMounted = true;

    const loadExplorer = async () => {
      setLoading(true);
      setError(null);
      setMetadataError(null);
      setSelectedPath(null);
      setSelectedNode(null);
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = null;
      }
      setPreview({
        kind: 'none',
        status: 'idle',
        url: null,
        error: null
      });

      try {
        const result = await fetchBookExplorerData(
          book.publisher,
          book.bookName,
          token,
          tokenType
        );

        if (!isMounted) {
          return;
        }

        if (result.tree) {
          setTree(normalizeRootNode(result.tree, book));
        } else {
          setTree(null);
          if (result.treeError) {
            console.error('Unable to load book contents', result.treeError);
            setError('Unable to load book contents.');
          }
        }

        if (result.config) {
          setMetadata(buildMetadata(result.config, book));
        } else {
          setMetadata(buildMetadata(null, book));
          if (result.configError) {
            console.error('Unable to load book metadata', result.configError);
            setMetadataError('Unable to load config.json metadata.');
          }
        }
      } catch (loadError) {
        if (!isMounted) {
          return;
        }
        console.error('Unable to load book explorer data', loadError);
        setTree(null);
        setMetadata(buildMetadata(null, book));
        setError('Unable to load book contents.');
        setMetadataError('Unable to load config.json metadata.');
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void loadExplorer();

    return () => {
      isMounted = false;
    };
  }, [open, book, token, tokenType]);

  useEffect(() => {
    if (!open) {
      return;
    }

    if (!book || !token) {
      setPreview({
        kind: 'none',
        status: 'idle',
        url: null,
        error: null
      });
      return;
    }

    const kind = inferPreviewKind(selectedNode);

    if (!selectedNode || kind === 'none') {
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = null;
      }
      setPreview({
        kind,
        status: 'idle',
        url: null,
        error: null
      });
      return;
    }

    if (kind === 'unsupported') {
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = null;
      }
      setPreview({
        kind,
        status: 'idle',
        url: null,
        error: null
      });
      return;
    }

    const controller = new AbortController();

    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }

    setPreview({
      kind,
      status: 'loading',
      url: null,
      error: null
    });

    const rangeHeader = kind === 'image' ? undefined : 'bytes=0-';

    downloadBookObject(
      book.publisher,
      book.bookName,
      selectedNode.relativePath,
      token,
      tokenType,
      {
        range: rangeHeader,
        signal: controller.signal,
        cache: 'no-store'
      }
    )
      .then((blob) => {
        if (controller.signal.aborted) {
          return;
        }
        const objectUrl = URL.createObjectURL(blob);
        previewUrlRef.current = objectUrl;
        setPreview({
          kind,
          status: 'ready',
          url: objectUrl,
          error: null
        });
      })
      .catch((previewError) => {
        if (controller.signal.aborted) {
          return;
        }
        console.error('Failed to load preview', previewError);
        setPreview({
          kind,
          status: 'error',
          url: null,
          error: 'Unable to load preview.'
        });
      });

    return () => {
      controller.abort();
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = null;
      }
    };
  }, [open, book, token, tokenType, selectedNode]);

  const handleDownload = async (node: ExplorerNode) => {
    if (!book || !token) {
      return;
    }

    try {
      const blob = await downloadBookObject(book.publisher, book.bookName, node.relativePath, token, tokenType);
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = node.name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(blobUrl);
      setFeedback({ severity: 'success', message: `Downloading ${node.name}` });
    } catch (downloadError) {
      console.error('Failed to download book object', downloadError);
      setFeedback({ severity: 'error', message: 'Unable to download the selected file.' });
    }
  };

  const handleCopyPath = async (node: ExplorerNode) => {
    try {
      if (!navigator.clipboard) {
        throw new Error('Clipboard access is unavailable');
      }
      await navigator.clipboard.writeText(node.path);
      setFeedback({ severity: 'success', message: 'Storage path copied to clipboard.' });
    } catch (copyError) {
      console.error('Failed to copy storage path', copyError);
      setFeedback({ severity: 'error', message: 'Unable to copy the storage path.' });
    }
  };

  const metadataEntries = useMemo(() => {
    if (!metadata) {
      return [];
    }

    return [
      { label: 'Publisher', value: metadata.publisher ?? 'Unknown' },
      { label: 'Book', value: metadata.bookName ?? (book?.bookName ?? 'Unknown') },
      { label: 'Language', value: metadata.language ?? 'Unknown' },
      { label: 'Category', value: metadata.category ?? 'Unknown' },
      { label: 'Version', value: metadata.version ?? 'Unknown' },
      { label: 'Status', value: metadata.status ?? 'Unknown' },
      { label: 'Created', value: formatDateTime(metadata.createdAt) },
      { label: 'Updated', value: formatDateTime(metadata.updatedAt) }
    ];
  }, [metadata, book]);

  const renderPreviewContent = () => {
    if (!selectedNode || selectedNode.type !== 'file') {
      return (
        <Typography variant="body2" color="text.secondary">
          Select a file from the tree to preview supported media.
        </Typography>
      );
    }

    if (preview.kind === 'unsupported') {
      return (
        <Typography variant="body2" color="text.secondary">
          Preview unavailable for this file type. Use the download action to inspect the content.
        </Typography>
      );
    }

    if (preview.status === 'loading') {
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <CircularProgress size={20} aria-label="Loading preview" />
          <Typography variant="body2">Preparing preview…</Typography>
        </Box>
      );
    }

    if (preview.status === 'error') {
      return (
        <Alert severity="error">
          {preview.error ?? 'Unable to load preview.'}
        </Alert>
      );
    }

    if (preview.status === 'ready' && preview.url) {
      if (preview.kind === 'image') {
        return (
          <Box
            component="img"
            src={preview.url}
            alt={`Preview of ${selectedNode.name}`}
            sx={{
              maxWidth: '100%',
              borderRadius: 1,
              border: (theme) => `1px solid ${theme.palette.divider}`,
              backgroundColor: 'background.paper'
            }}
            onError={() => {
              if (previewUrlRef.current) {
                URL.revokeObjectURL(previewUrlRef.current);
                previewUrlRef.current = null;
              }
              setPreview({
                kind: 'image',
                status: 'error',
                url: null,
                error: 'Image preview failed to load.'
              });
            }}
          />
        );
      }

      if (preview.kind === 'audio') {
        return (
          <audio
            key={selectedNode.path}
            controls
            src={preview.url}
            aria-label="Audio preview"
            preload="metadata"
            style={{ width: '100%' }}
            onError={() => {
              if (previewUrlRef.current) {
                URL.revokeObjectURL(previewUrlRef.current);
                previewUrlRef.current = null;
              }
              setPreview((current) => ({
                ...current,
                status: 'error',
                error: 'Playback failed. Try downloading the file instead.',
                url: null
              }));
            }}
          >
            Your browser does not support audio playback.
          </audio>
        );
      }

      if (preview.kind === 'video') {
        return (
          <Box sx={{ width: '100%' }}>
            <video
              key={selectedNode.path}
              controls
              src={preview.url}
              aria-label="Video preview"
              preload="metadata"
              style={{ width: '100%', maxHeight: 240, borderRadius: 8 }}
              onError={() => {
                if (previewUrlRef.current) {
                  URL.revokeObjectURL(previewUrlRef.current);
                  previewUrlRef.current = null;
                }
                setPreview((current) => ({
                  ...current,
                  status: 'error',
                  error: 'Playback failed. Try downloading the file instead.',
                  url: null
                }));
              }}
            >
              Your browser does not support video playback.
            </video>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
              Streaming uses authenticated range requests. Large files may take a moment to buffer.
            </Typography>
          </Box>
        );
      }
    }

    return (
      <Typography variant="body2" color="text.secondary">
        Preview unavailable.
      </Typography>
    );
  };

  return (
    <Drawer anchor="right" open={open} onClose={onClose} keepMounted>
      <Box sx={{ width: 420, display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', px: 3, py: 2 }}>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6" component="h2">
              {book?.bookName ?? 'Book Explorer'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Inspect stored assets and metadata for this book.
            </Typography>
          </Box>
          <IconButton onClick={onClose} aria-label="Close book explorer">
            <CloseIcon />
          </IconButton>
        </Box>
        <Divider />

        <Box sx={{ p: 3, overflowY: 'auto', flexGrow: 1 }}>
          {loading ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <CircularProgress size={24} aria-label="Loading book contents" />
              <Typography variant="body2">Loading book contents…</Typography>
            </Box>
          ) : null}

          {error ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          ) : null}

          {metadataError ? (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {metadataError}
            </Alert>
          ) : null}

          {feedback ? (
            <Alert
              severity={feedback.severity}
              sx={{ mb: 2 }}
              onClose={() => setFeedback(null)}
            >
              {feedback.message}
            </Alert>
          ) : null}

          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              Metadata
            </Typography>
            {metadataEntries.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No metadata available.
              </Typography>
            ) : (
              <Stack spacing={1}>
                {metadataEntries.map((entry) => (
                  <Box key={entry.label} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                      {entry.label}
                    </Typography>
                    <Typography variant="body2" sx={{ textAlign: 'right' }}>
                      {entry.value}
                    </Typography>
                  </Box>
                ))}
              </Stack>
            )}
          </Box>

          <Divider sx={{ mb: 3 }} />

          <Typography variant="subtitle1" gutterBottom>
            Stored Files
          </Typography>
          {tree ? (
            <ExplorerTree
              root={tree}
              selectedPath={selectedPath}
              onSelect={(node) => {
                setSelectedPath(node.path);
                setSelectedNode(node);
              }}
              onDownload={handleDownload}
              onCopyPath={handleCopyPath}
            />
          ) : !loading && !error ? (
            <Typography variant="body2" color="text.secondary">
              No files found for this book.
            </Typography>
          ) : null}

          <Divider sx={{ my: 3 }} />

          <Typography variant="subtitle1" gutterBottom>
            Preview
          </Typography>
          {renderPreviewContent()}
        </Box>

        <Box sx={{ px: 3, py: 2, borderTop: (theme) => `1px solid ${theme.palette.divider}` }}>
          <Button variant="outlined" fullWidth onClick={onClose}>
            Close
          </Button>
        </Box>
      </Box>
    </Drawer>
  );
};

export default BookExplorerDrawer;
