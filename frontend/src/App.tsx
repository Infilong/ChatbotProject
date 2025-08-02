import React, { useState, useEffect } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { theme } from './theme';
import LoginPage from './components/LoginPage';
import ChatPage from './components/ChatPage';
import { storageUtils } from './utils/storageUtils';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing session on app load
  useEffect(() => {
    const sessionData = storageUtils.getSession();
    if (sessionData?.isLoggedIn && sessionData.username) {
      setIsLoggedIn(true);
      setUsername(sessionData.username);
    }
    setIsLoading(false);
  }, []);

  const handleLogin = (inputUsername: string, password: string) => {
    // Simple demo authentication - in real app, this would call an API
    if (inputUsername && password) {
      setUsername(inputUsername);
      setIsLoggedIn(true);
      
      // Save session to localStorage
      storageUtils.saveSession({
        isLoggedIn: true,
        username: inputUsername,
        loginTime: new Date().toISOString()
      });
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setUsername('');
    
    // Clear session data
    storageUtils.clearSession();
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
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {isLoggedIn ? (
        <ChatPage username={username} onLogout={handleLogout} />
      ) : (
        <LoginPage onLogin={handleLogin} />
      )}
    </ThemeProvider>
  );
}

export default App;
