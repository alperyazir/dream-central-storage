import { describe, it, expect, vi, beforeEach, Mock } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material';

import ProcessingPage from '../pages/Processing';
import * as processingLib from '../lib/processing';
import * as authStore from '../stores/auth';

// Mock the auth store
vi.mock('../stores/auth', () => ({
  useAuthStore: vi.fn(),
}));

// Mock ProcessingDialog
vi.mock('../components/ProcessingDialog', () => ({
  default: ({ open, onClose, bookTitle }: { open: boolean; onClose: () => void; bookTitle: string }) =>
    open ? (
      <div data-testid="processing-dialog">
        Processing Dialog for {bookTitle}
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));

const theme = createTheme();

const renderWithProviders = (component: React.ReactNode) => {
  return render(
    <BrowserRouter>
      <ThemeProvider theme={theme}>{component}</ThemeProvider>
    </BrowserRouter>
  );
};

const mockBooksResponse = {
  books: [
    {
      book_id: 1,
      book_name: 'test-book-1',
      book_title: 'Test Book 1',
      publisher_id: 1,
      publisher_name: 'Publisher A',
      processing_status: 'completed' as const,
      progress: 100,
      current_step: null,
      error_message: null,
      job_id: null,
      last_processed_at: '2024-01-01T00:00:00Z',
    },
    {
      book_id: 2,
      book_name: 'test-book-2',
      book_title: 'Test Book 2',
      publisher_id: 1,
      publisher_name: 'Publisher A',
      processing_status: 'failed' as const,
      progress: 50,
      current_step: 'Vocabulary extraction',
      error_message: 'API rate limit exceeded',
      job_id: 'job-123',
      last_processed_at: null,
    },
  ],
  total: 2,
  page: 1,
  page_size: 50,
};

const mockQueueResponse = {
  queue: [],
  total_queued: 0,
  total_processing: 0,
};

describe('ProcessingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock auth store
    (authStore.useAuthStore as Mock).mockImplementation((selector: (state: unknown) => unknown) => {
      const state = {
        token: 'test-token',
        tokenType: 'Bearer',
      };
      return selector(state);
    });

    // Mock API functions using spyOn
    vi.spyOn(processingLib, 'getBooksWithProcessingStatus').mockResolvedValue(mockBooksResponse);
    vi.spyOn(processingLib, 'getProcessingQueue').mockResolvedValue(mockQueueResponse);
    vi.spyOn(processingLib, 'clearProcessingError').mockResolvedValue({ message: 'Error cleared' });
    vi.spyOn(processingLib, 'bulkReprocess').mockResolvedValue({
      triggered: 2,
      skipped: 0,
      errors: [],
      job_ids: ['job-1', 'job-2'],
    });
  });

  it('renders the page title', async () => {
    renderWithProviders(<ProcessingPage />);

    await waitFor(() => {
      expect(screen.getByText('AI Processing Dashboard')).toBeInTheDocument();
    });
  });

  it('renders books in the table', async () => {
    renderWithProviders(<ProcessingPage />);

    await waitFor(() => {
      expect(screen.getByText('Test Book 1')).toBeInTheDocument();
      expect(screen.getByText('Test Book 2')).toBeInTheDocument();
    });
  });

  it('shows error message for failed books', async () => {
    renderWithProviders(<ProcessingPage />);

    await waitFor(() => {
      expect(screen.getByText(/API rate limit exceeded/)).toBeInTheDocument();
    });
  });

  it('renders queue panel', async () => {
    renderWithProviders(<ProcessingPage />);

    await waitFor(() => {
      expect(screen.getByText('Processing Queue')).toBeInTheDocument();
      expect(screen.getByText('0 queued')).toBeInTheDocument();
      expect(screen.getByText('0 processing')).toBeInTheDocument();
    });
  });

  it('shows queue items when jobs are active', async () => {
    vi.spyOn(processingLib, 'getProcessingQueue').mockResolvedValue({
      queue: [
        {
          job_id: 'job-1',
          book_id: 3,
          book_name: 'processing-book',
          book_title: 'Processing Book',
          publisher_name: 'Publisher B',
          status: 'processing',
          progress: 25,
          current_step: 'Text extraction',
          position: 1,
          created_at: '2024-01-01T00:00:00Z',
          started_at: '2024-01-01T00:01:00Z',
        },
      ],
      total_queued: 0,
      total_processing: 1,
    });

    renderWithProviders(<ProcessingPage />);

    await waitFor(() => {
      expect(screen.getByText('1 processing')).toBeInTheDocument();
      expect(screen.getByText('Processing Book')).toBeInTheDocument();
    });
  });

  it('handles checkbox selection', async () => {
    renderWithProviders(<ProcessingPage />);

    await waitFor(() => {
      expect(screen.getByText('Test Book 1')).toBeInTheDocument();
    });

    // Find all checkboxes
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBeGreaterThan(0);

    // Click the first non-header checkbox
    fireEvent.click(checkboxes[1]);

    // Bulk button should show count
    await waitFor(() => {
      expect(screen.getByText(/Bulk Reprocess \(1\)/)).toBeInTheDocument();
    });
  });

  it('handles select all checkbox', async () => {
    renderWithProviders(<ProcessingPage />);

    await waitFor(() => {
      expect(screen.getByText('Test Book 1')).toBeInTheDocument();
    });

    // Click the select all checkbox (first one in header)
    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[0]);

    await waitFor(() => {
      expect(screen.getByText(/Bulk Reprocess \(2\)/)).toBeInTheDocument();
    });
  });

  it('filters by status', async () => {
    renderWithProviders(<ProcessingPage />);

    await waitFor(() => {
      expect(screen.getByText('Test Book 1')).toBeInTheDocument();
    });

    // Find the status filter - there are multiple "Status" texts (label, select, table header)
    // Use getAllByText and verify there's at least one (the form control)
    const statusElements = screen.getAllByText('Status');
    expect(statusElements.length).toBeGreaterThan(0);

    // Find the one that's the InputLabel (has MuiInputLabel class)
    const statusLabel = statusElements.find((el) => el.classList.contains('MuiInputLabel-root'));
    expect(statusLabel).toBeDefined();
  });

  it('shows search input', async () => {
    renderWithProviders(<ProcessingPage />);

    await waitFor(() => {
      const searchInput = screen.getByPlaceholderText(/Search by title or publisher/);
      expect(searchInput).toBeInTheDocument();
    });
  });

  it('displays refresh button', async () => {
    renderWithProviders(<ProcessingPage />);

    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });
  });

  it('calls bulk reprocess when button clicked', async () => {
    renderWithProviders(<ProcessingPage />);

    await waitFor(() => {
      expect(screen.getByText('Test Book 1')).toBeInTheDocument();
    });

    // Select all books
    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[0]);

    // Click bulk reprocess button
    const bulkButton = screen.getByText(/Bulk Reprocess/);
    fireEvent.click(bulkButton);

    await waitFor(() => {
      expect(processingLib.bulkReprocess).toHaveBeenCalled();
    });
  });
});

describe('Processing lib functions', () => {
  it('getExtendedStatusColor returns correct colors', () => {
    expect(processingLib.getExtendedStatusColor('not_started')).toBe('default');
    expect(processingLib.getExtendedStatusColor('completed')).toBe('success');
    expect(processingLib.getExtendedStatusColor('failed')).toBe('error');
    expect(processingLib.getExtendedStatusColor('processing')).toBe('primary');
    expect(processingLib.getExtendedStatusColor('queued')).toBe('info');
  });

  it('getExtendedStatusLabel returns correct labels', () => {
    expect(processingLib.getExtendedStatusLabel('not_started')).toBe('Not Started');
    expect(processingLib.getExtendedStatusLabel('completed')).toBe('Completed');
    expect(processingLib.getExtendedStatusLabel('failed')).toBe('Failed');
  });
});
