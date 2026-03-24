import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import App from './App';
import { useThemeStore } from './stores/theme';
import './index.css';

const ThemeWrapper = ({ children }: { children: React.ReactNode }) => {
  const mode = useThemeStore((state) => state.mode);

  React.useEffect(() => {
    document.documentElement.classList.toggle('dark', mode === 'dark');
  }, [mode]);

  return <>{children}</>;
};

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <ThemeWrapper>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ThemeWrapper>
  </React.StrictMode>
);
