import { describe, it, expect, vi, beforeEach, Mock } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material';

import ProcessingSettingsPage from '../pages/ProcessingSettings';
import * as processingLib from '../lib/processing';
import * as authStore from '../stores/auth';

// Mock the auth store
vi.mock('../stores/auth', () => ({
  useAuthStore: vi.fn(),
}));

const theme = createTheme();

const renderWithProviders = (component: React.ReactNode) => {
  return render(
    <BrowserRouter>
      <ThemeProvider theme={theme}>{component}</ThemeProvider>
    </BrowserRouter>
  );
};

const mockSettings = {
  ai_auto_process_on_upload: true,
  ai_auto_process_skip_existing: true,
  llm_primary_provider: 'deepseek',
  llm_fallback_provider: 'gemini',
  tts_primary_provider: 'edge',
  tts_fallback_provider: 'azure',
  queue_max_concurrency: 3,
  vocabulary_max_words_per_module: 50,
  audio_generation_languages: 'en,tr',
  audio_generation_concurrency: 5,
};

describe('ProcessingSettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock auth store
    (authStore.useAuthStore as unknown as Mock).mockImplementation((selector: (state: unknown) => unknown) => {
      const state = {
        token: 'test-token',
        tokenType: 'Bearer',
      };
      return selector(state);
    });

    // Mock API functions
    vi.spyOn(processingLib, 'getProcessingSettings').mockResolvedValue(mockSettings);
    vi.spyOn(processingLib, 'updateProcessingSettings').mockResolvedValue(mockSettings);
  });

  it('renders settings form with loading state initially', () => {
    // Use pending promise to keep loading state
    vi.spyOn(processingLib, 'getProcessingSettings').mockReturnValue(new Promise(() => {}));

    renderWithProviders(<ProcessingSettingsPage />);

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders all settings sections after loading', async () => {
    renderWithProviders(<ProcessingSettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('AI Processing Settings')).toBeInTheDocument();
    });

    // Check for main sections
    expect(screen.getByText('Auto-Processing')).toBeInTheDocument();
    expect(screen.getByText('LLM Providers')).toBeInTheDocument();
    expect(screen.getByText('TTS Providers (Audio Generation)')).toBeInTheDocument();
    expect(screen.getByText('Vocabulary Extraction')).toBeInTheDocument();
    expect(screen.getByText('Audio Generation')).toBeInTheDocument();
    expect(screen.getByText('Processing Queue')).toBeInTheDocument();
  });

  it('loads current settings on mount', async () => {
    renderWithProviders(<ProcessingSettingsPage />);

    await waitFor(() => {
      expect(processingLib.getProcessingSettings).toHaveBeenCalledWith('test-token', 'Bearer');
    });
  });

  it('displays auto-process toggle with correct initial state', async () => {
    renderWithProviders(<ProcessingSettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('Auto-Processing')).toBeInTheDocument();
    });

    // Check that auto-process toggle is present
    expect(screen.getByLabelText('Auto-process books on upload')).toBeInTheDocument();
    expect(screen.getByLabelText('Skip already processed books')).toBeInTheDocument();
  });

  it('saves settings when save button is clicked', async () => {
    renderWithProviders(<ProcessingSettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('Save Settings')).toBeInTheDocument();
    });

    const saveButton = screen.getByText('Save Settings');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(processingLib.updateProcessingSettings).toHaveBeenCalled();
    });
  });

  it('shows success message on successful save', async () => {
    renderWithProviders(<ProcessingSettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('Save Settings')).toBeInTheDocument();
    });

    const saveButton = screen.getByText('Save Settings');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(/Settings saved successfully/)).toBeInTheDocument();
    });
  });

  it('shows error message on save failure', async () => {
    vi.spyOn(processingLib, 'updateProcessingSettings').mockRejectedValue(new Error('Network error'));

    renderWithProviders(<ProcessingSettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('Save Settings')).toBeInTheDocument();
    });

    const saveButton = screen.getByText('Save Settings');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('Failed to save settings')).toBeInTheDocument();
    });
  });

  it('refreshes settings when refresh button is clicked', async () => {
    renderWithProviders(<ProcessingSettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });

    // Clear the initial call count
    vi.clearAllMocks();
    vi.spyOn(processingLib, 'getProcessingSettings').mockResolvedValue(mockSettings);

    const refreshButton = screen.getByText('Refresh');
    fireEvent.click(refreshButton);

    await waitFor(() => {
      expect(processingLib.getProcessingSettings).toHaveBeenCalled();
    });
  });

  it('shows error message on load failure', async () => {
    vi.spyOn(processingLib, 'getProcessingSettings').mockRejectedValue(new Error('Load error'));

    renderWithProviders(<ProcessingSettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load settings')).toBeInTheDocument();
    });
  });
});
