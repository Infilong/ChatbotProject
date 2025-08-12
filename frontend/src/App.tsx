import React, { useState, useEffect } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { theme } from './theme';
import LoginPage from './components/LoginPage';
import ChatPage from './components/ChatPage';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastProvider } from './components/Toast';
import { LanguageProvider } from './contexts/LanguageContext';
import { ConversationHistoryProvider } from './contexts/ConversationHistoryContext';
import authService from './services/authService';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [userData, setUserData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing authentication on app load
  useEffect(() => {
    const checkAuth = async () => {
      try {
        if (authService.isAuthenticated()) {
          // Validate token with backend
          const validation = await authService.validateToken();
          if (validation.valid && validation.user) {
            setIsLoggedIn(true);
            setUsername(validation.user.username);
            setUserData(validation.user);
          } else {
            // Token is invalid, clear it
            await authService.logout();
          }
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        await authService.logout();
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const handleLogin = (inputUsername: string, user: any) => {
    setUsername(inputUsername);
    setUserData(user);
    setIsLoggedIn(true);
  };

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setIsLoggedIn(false);
      setUsername('');
      setUserData(null);
    }
  };

  // Show loading screen while checking for existing session
  if (isLoading) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          backgroundColor: '#0288D1'
        }}>
          <div style={{ color: 'white', fontSize: '1.2rem' }}>Loading...</div>
        </div>
      </ThemeProvider>
    );
  }

  return (
    <ErrorBoundary>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <LanguageProvider>
          <ConversationHistoryProvider>
            <ToastProvider>
              {isLoggedIn ? (
                <ChatPage username={username} onLogout={handleLogout} />
              ) : (
                <LoginPage onLogin={handleLogin} />
              )}
            </ToastProvider>
          </ConversationHistoryProvider>
        </LanguageProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
