import { createTheme } from '@mui/material/styles';

// Material Design 3 Ocean Blue Theme
export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#006A6B', // Ocean Blue
      light: '#4FB3D9',
      dark: '#004D40',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#0288D1', // Light Ocean Blue
      light: '#4FC3F7',
      dark: '#01579B',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#FAFAFA', // Almost white
      paper: '#FFFFFF', // Pure white
    },
    text: {
      primary: '#1C1B1F',
      secondary: '#49454F',
    },
  },
  typography: {
    fontFamily: [
      'Roboto',
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
    h3: {
      fontWeight: 500,
      fontSize: '1.75rem',
    },
    button: {
      textTransform: 'none' as const,
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 20,
          fontWeight: 500,
          textTransform: 'none',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 12,
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        },
      },
    },
  },
});