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
} from '@mui/material';
import { Person, Lock } from '@mui/icons-material';
import LanguageSelector from './LanguageSelector';
import { useLanguage } from '../contexts/LanguageContext';

interface LoginPageProps {
  onLogin: (username: string, password: string) => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { language, setLanguage } = useLanguage();

  // Language translations
  const translations = {
    en: {
      title: 'DataPro Solutions',
      subtitle: 'Intelligent Customer Support',
      username: 'Username',
      password: 'Password',
      signIn: 'Sign In',
      demo: 'Demo credentials: admin / password',
      validation: 'Please enter both username and password'
    },
    ja: {
      title: 'DataProソリューション',
      subtitle: 'インテリジェントカスタマーサポート',
      username: 'ユーザー名',
      password: 'パスワード',
      signIn: 'サインイン',
      demo: 'デモ認証情報: admin / password',
      validation: 'ユーザー名とパスワードの両方を入力してください'
    }
  };

  const t = translations[language];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Basic validation
    if (!username.trim() || !password.trim()) {
      setError(t.validation);
      return;
    }

    // Clear error and call onLogin
    setError('');
    onLogin(username, password);
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
                }}
              >
                {t.signIn}
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