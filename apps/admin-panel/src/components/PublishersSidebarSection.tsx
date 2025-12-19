import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Collapse,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  CircularProgress,
  Typography,
  Chip,
} from '@mui/material';
import ExpandLess from '@mui/icons-material/ExpandLess';
import ExpandMore from '@mui/icons-material/ExpandMore';
import BusinessIcon from '@mui/icons-material/Business';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import FolderIcon from '@mui/icons-material/Folder';
import AddIcon from '@mui/icons-material/Add';

import { fetchPublishers, type Publisher } from '../lib/publishers';
import { useAuthStore } from '../stores/auth';

const STORAGE_KEY = 'publishersSidebarState';

interface SidebarState {
  publishersExpanded: boolean;
  expandedPublishers: number[];
}

const loadState = (): SidebarState => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error('Failed to load sidebar state:', error);
  }
  return { publishersExpanded: false, expandedPublishers: [] };
};

const saveState = (state: SidebarState) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (error) {
    console.error('Failed to save sidebar state:', error);
  }
};

const PublishersSidebarSection = () => {
  const navigate = useNavigate();
  const token = useAuthStore((state) => state.token);
  const tokenType = useAuthStore((state) => state.tokenType);

  const [publishers, setPublishers] = useState<Publisher[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [publishersExpanded, setPublishersExpanded] = useState(() => loadState().publishersExpanded);
  const [expandedPublishers, setExpandedPublishers] = useState<number[]>(
    () => loadState().expandedPublishers
  );

  useEffect(() => {
    saveState({ publishersExpanded, expandedPublishers });
  }, [publishersExpanded, expandedPublishers]);

  useEffect(() => {
    if (!token) return;

    const loadPublishers = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchPublishers(token, tokenType || 'Bearer');
        setPublishers(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Failed to fetch publishers:', err);
        setError('Failed to load publishers');
      } finally {
        setLoading(false);
      }
    };

    loadPublishers();
  }, [token, tokenType]);

  const handlePublishersToggle = () => {
    setPublishersExpanded(!publishersExpanded);
  };

  const handlePublisherToggle = (publisherId: number) => {
    setExpandedPublishers((prev) =>
      prev.includes(publisherId) ? prev.filter((id) => id !== publisherId) : [...prev, publisherId]
    );
  };

  const handlePublisherClick = (publisherId: number) => {
    navigate(`/publishers/${publisherId}`);
  };

  const handleAddPublisher = () => {
    navigate('/publishers');
  };

  const getStatusColor = (status: string): 'success' | 'default' | 'warning' => {
    switch (status) {
      case 'active':
        return 'success';
      case 'suspended':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <>
      <ListItemButton onClick={handlePublishersToggle} sx={{ borderRadius: '8px' }}>
        <ListItemIcon sx={{ minWidth: 36 }}>
          <BusinessIcon fontSize="small" />
        </ListItemIcon>
        <ListItemText primary="Publishers" />
        {publishersExpanded ? <ExpandLess /> : <ExpandMore />}
      </ListItemButton>

      <Collapse in={publishersExpanded} timeout="auto" unmountOnExit>
        <List component="div" disablePadding>
          {loading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
              <CircularProgress size={20} />
            </Box>
          )}

          {error && (
            <Box sx={{ px: 2, py: 1 }}>
              <Typography variant="caption" color="error">
                {error}
              </Typography>
            </Box>
          )}

          {!loading &&
            !error &&
            publishers.map((publisher) => {
              const isExpanded = expandedPublishers.includes(publisher.id);
              return (
                <Box key={publisher.id}>
                  <ListItemButton
                    sx={{ pl: 4, borderRadius: '8px', mx: 0.5 }}
                    onClick={() => handlePublisherToggle(publisher.id)}
                  >
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <BusinessIcon fontSize="small" />
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <span>{publisher.display_name || publisher.name}</span>
                          <Chip
                            label={publisher.status}
                            size="small"
                            color={getStatusColor(publisher.status)}
                            sx={{ height: 16, fontSize: '0.65rem' }}
                          />
                        </Box>
                      }
                      primaryTypographyProps={{ variant: 'body2' }}
                    />
                    {isExpanded ? <ExpandLess /> : <ExpandMore />}
                  </ListItemButton>

                  <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                    <List component="div" disablePadding>
                      <ListItemButton
                        sx={{ pl: 6, borderRadius: '8px', mx: 0.5 }}
                        onClick={() => handlePublisherClick(publisher.id)}
                      >
                        <ListItemIcon sx={{ minWidth: 36 }}>
                          <MenuBookIcon fontSize="small" />
                        </ListItemIcon>
                        <ListItemText
                          primary="Books"
                          primaryTypographyProps={{ variant: 'body2' }}
                        />
                      </ListItemButton>

                      <ListItemButton
                        sx={{ pl: 6, borderRadius: '8px', mx: 0.5 }}
                        onClick={() => handlePublisherClick(publisher.id)}
                      >
                        <ListItemIcon sx={{ minWidth: 36 }}>
                          <FolderIcon fontSize="small" />
                        </ListItemIcon>
                        <ListItemText
                          primary="Assets"
                          primaryTypographyProps={{ variant: 'body2' }}
                        />
                      </ListItemButton>
                    </List>
                  </Collapse>
                </Box>
              );
            })}

          {!loading && !error && (
            <ListItemButton
              sx={{ pl: 4, borderRadius: '8px', mx: 0.5 }}
              onClick={handleAddPublisher}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>
                <AddIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText
                primary="Add Publisher"
                primaryTypographyProps={{ variant: 'body2', fontStyle: 'italic' }}
              />
            </ListItemButton>
          )}
        </List>
      </Collapse>
    </>
  );
};

export default PublishersSidebarSection;
