import { MemoryRouter } from 'react-router-dom';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import App from '../App';

const renderApp = (initialEntries: string[] = ['/']) =>
  render(
    <MemoryRouter initialEntries={initialEntries}>
      <App />
    </MemoryRouter>
  );

describe('App routing', () => {
  it('renders navigation and dashboard content by default', () => {
    renderApp();

    expect(screen.getByRole('navigation', { name: /primary/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByText(/Welcome to the Dream Central Storage admin panel/i)).toBeInTheDocument();
  });

  it('navigates to the login page when the login link is clicked', async () => {
    const user = userEvent.setup();
    renderApp(['/dashboard']);

    await act(async () => {
      await user.click(screen.getByRole('link', { name: /login/i }));
    });

    expect(await screen.findByRole('heading', { name: /admin login/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });
});
