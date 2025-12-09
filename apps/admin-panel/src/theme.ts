import { createTheme, PaletteMode } from '@mui/material/styles';

const turquoise = {
  50: '#f2fbf9',
  100: '#d6f4ef',
  200: '#ace8df',
  300: '#7ed9ce',
  400: '#52c7bc',
  500: '#2cb8ad',
  600: '#189b92',
  700: '#0f7b75',
  800: '#0b5a56',
  900: '#083d3c'
};

const denim = {
  main: '#1b79b0',
  light: '#4ca0d0',
  dark: '#12557c'
};

export const createAppTheme = (mode: PaletteMode) => createTheme({
  palette: {
    mode,
    primary: {
      main: turquoise[500],
      light: turquoise[300],
      dark: turquoise[700],
      contrastText: '#ffffff'
    },
    secondary: {
      main: denim.main,
      light: denim.light,
      dark: denim.dark,
      contrastText: '#ffffff'
    },
    background: mode === 'light' ? {
      default: turquoise[50],
      paper: '#ffffff'
    } : {
      default: '#0a1929',
      paper: '#132f4c'
    },
    text: mode === 'light' ? {
      primary: '#04313d',
      secondary: '#0f5c65'
    } : {
      primary: '#e3f2fd',
      secondary: '#b0bec5'
    },
    divider: mode === 'light' ? '#b4e1e4' : '#1e4976',
    success: {
      main: '#16836a'
    },
    warning: {
      main: '#f59e0b'
    },
    error: {
      main: '#dc2626'
    }
  },
  typography: {
    fontFamily: '\'Inter\', system-ui, -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif',
    h1: {
      fontSize: '2.75rem',
      fontWeight: 700,
      letterSpacing: '-0.02em'
    },
    h2: {
      fontSize: '2.1rem',
      fontWeight: 700,
      letterSpacing: '-0.01em'
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600
    },
    button: {
      fontWeight: 600,
      textTransform: 'none'
    },
    subtitle1: {
      fontWeight: 500
    }
  },
  shape: {
    borderRadius: 12
  },
  components: {
    MuiButton: {
      defaultProps: {
        disableElevation: true
      },
      styleOverrides: {
        root: {
          borderRadius: 999,
          paddingInline: '1.25rem',
          paddingBlock: '0.65rem'
        }
      }
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 18
        }
      }
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundImage: 'linear-gradient(135deg, #0f7b75 0%, #1b79b0 100%)'
        }
      }
    },
    MuiTableHead: {
      styleOverrides: {
        root: ({ theme }) => ({
          backgroundColor: theme.palette.mode === 'light' ? turquoise[100] : theme.palette.background.paper
        })
      }
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 12
        }
      }
    }
  }
});

export const appTheme = createAppTheme('light');

export default appTheme;
