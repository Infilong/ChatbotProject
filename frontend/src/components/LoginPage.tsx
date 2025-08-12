import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Container,
  Alert,
  InputAdornment,
  CircularProgress,
} from '@mui/material';
import { Person, Lock } from '@mui/icons-material';
import LanguageSelector from './LanguageSelector';
import { useLanguage } from '../contexts/LanguageContext';
import authService, { AuthError } from '../services/authService';

interface LoginPageProps {
  onLogin: (username: string, userData: any) => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { language, setLanguage } = useLanguage();

  // Language translations
  const translations = {
    en: {
      title: 'DataPro Solutions',
      subtitle: 'Intelligent Customer Support',
      username: 'Username',
      password: 'Password',
      signIn: 'Sign In',
      demo: 'Register an account or contact admin for access',
      validation: 'Please enter both username and password',
      loginError: 'Login failed. Please check your credentials and try again.',
      networkError: 'Network error. Please check your connection and try again.'
    },
    ja: {
      title: 'DataProソリューション',
      subtitle: 'インテリジェントカスタマーサポート',
      username: 'ユーザー名',
      password: 'パスワード',
      signIn: 'サインイン',
      demo: 'アカウントを登録するか、管理者にお問い合わせください',
      validation: 'ユーザー名とパスワードの両方を入力してください',
      loginError: 'ログインに失敗しました。認証情報を確認して再度お試しください。',
      networkError: 'ネットワークエラーです。接続を確認して再度お試しください。'
    }
  };

  const t = translations[language];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Basic validation
    if (!username.trim() || !password.trim()) {
      setError(t.validation);
      return;
    }

    setError('');
    setLoading(true);

    try {
      // Use real authentication service
      const result = await authService.login({ username, password });
      
      if (result.success && result.user) {
        // Pass user data to parent component
        onLogin(result.user.username, result.user);
      } else {
        setError(result.message || t.loginError);
      }
    } catch (error: any) {
      console.error('Login error:', error);
      
      // Handle different types of errors
      if (error.error) {
        setError(error.error);
      } else if (error.message) {
        setError(error.message);
      } else {
        setError(t.networkError);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        height: '100%',
        backgroundColor: '#0288D1',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 2,
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
      }}
    >
      <Container maxWidth="sm">
        <Card
          sx={{
            padding: 4,
            borderRadius: 3,
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12)',
            position: 'relative',
          }}
        >
          {/* Language Selector */}
          <Box sx={{ position: 'absolute', top: 16, right: 16 }}>
            <LanguageSelector
              currentLanguage={language}
              onLanguageChange={setLanguage}
              variant="page"
            />
          </Box>
          
          <CardContent>
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <Typography variant="h3" component="h1" gutterBottom>
                {t.title}
              </Typography>
              <Typography variant="h6" color="text.secondary">
                {t.subtitle}
              </Typography>
            </Box>

            <form onSubmit={handleSubmit}>
              <Box sx={{ mb: 3 }}>
                <TextField
                  fullWidth
                  label={t.username}
                  variant="outlined"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  slotProps={{
                    input: {
                      startAdornment: (
                        <InputAdornment position="start">
                          <Person sx={{ color: 'action.active' }} />
                        </InputAdornment>
                      ),
                    },
                  }}
                />
              </Box>

              <Box sx={{ mb: 3 }}>
                <TextField
                  fullWidth
                  label={t.password}
                  type="password"
                  variant="outlined"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  slotProps={{
                    input: {
                      startAdornment: (
                        <InputAdornment position="start">
                          <Lock sx={{ color: 'action.active' }} />
                        </InputAdornment>
                      ),
                    },
                  }}
                />
              </Box>

              {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  {error}
                </Alert>
              )}

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={loading}
                sx={{
                  py: 1.5,
                  fontSize: '1.1rem',
                  fontWeight: 600,
                  backgroundColor: 'white',
                  color: '#0288D1',
                  border: '2px solid #0288D1',
                  '&:hover': {
                    backgroundColor: '#1565C0',
                    color: 'white',
                    transform: 'translateY(-2px)',
                    boxShadow: '0 4px 15px rgba(21, 101, 192, 0.3)',
                  },
                  '&:disabled': {
                    backgroundColor: '#f5f5f5',
                    color: '#999',
                    border: '2px solid #ccc',
                  },
                }}
              >
                {loading ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CircularProgress size={20} />
                    <span>Signing in...</span>
                  </Box>
                ) : (
                  t.signIn
                )}
              </Button>
            </form>

            <Box sx={{ mt: 3, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                {t.demo}
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
};

export default LoginPage;