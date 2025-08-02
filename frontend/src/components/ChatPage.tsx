import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Button,
  Typography,
  AppBar,
  Toolbar,
  Container,
  Chip,
} from '@mui/material';
import { 
  SupportAgent, 
  AccountCircle, 
  ExitToApp, 
  HeadsetMic
} from '@mui/icons-material';
import { Message } from '../types/Message';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { storageUtils } from '../utils/storageUtils';
import { messageUtils } from '../utils/messageUtils';
import { chatService } from '../services/chatService';

interface ChatPageProps {
  username: string;
  onLogout: () => void;
}

const ChatPage: React.FC<ChatPageProps> = ({ username, onLogout }) => {
  const [messages, setMessages] = useState<Message[]>([]);

  // Load saved messages on component mount
  useEffect(() => {
    const savedMessages = storageUtils.getMessages();
    
    if (savedMessages.length > 0) {
      setMessages(savedMessages);
    } else {
      // No saved messages, start with welcome message
      const welcomeMessage = messageUtils.createWelcomeMessage(username);
      setMessages([welcomeMessage]);
    }
  }, [username]);

  // Save messages to localStorage whenever messages change
  useEffect(() => {
    if (messages.length > 0) {
      storageUtils.saveMessages(messages);
    }
  }, [messages]);

  const handleSendMessage = async (message: string, file?: File) => {
    if (!messageUtils.validateMessage(message, file)) return;

    // Add user message
    const userMessage = messageUtils.createMessage(message, 'user', file);
    setMessages(prev => [...prev, userMessage]);

    // Generate bot response
    try {
      const response = await chatService.generateResponse(userMessage);
      setMessages(prev => [...prev, response.message]);
    } catch (error) {
      console.error('Error generating bot response:', error);
    }
  };

  const handleFeedback = (messageId: string, feedback: 'up' | 'down') => {
    setMessages(prev => messageUtils.updateMessageFeedback(prev, messageId, feedback));
  };

  const handleHumanService = () => {
    const serviceMessage = chatService.createHumanServiceMessage();
    setMessages(prev => [...prev, serviceMessage]);
  };



  return (
    <Box sx={{ 
      minHeight: '100vh',
      height: '100%',
      backgroundColor: 'white',
      position: 'relative',
      top: 0, left: 0, right: 0, bottom: 0,
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <AppBar position="fixed" sx={{ backgroundColor: '#1565C0', zIndex: 1100 }}>
        <Toolbar>
          <SupportAgent sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            DataPro Support Chat
          </Typography>
          <Chip
            avatar={<AccountCircle />}
            label={username}
            variant="outlined"
            sx={{ 
              color: 'white', 
              borderColor: 'white', 
              mr: 2,
              '& .MuiAvatar-root': {
                backgroundColor: 'transparent',
                color: 'white',
              }
            }}
          />
          
          <Button
            color="inherit"
            startIcon={<ExitToApp />}
            onClick={onLogout}
          >
            Logout
          </Button>
        </Toolbar>
      </AppBar>

      {/* Messages Container */}
      <Container 
        maxWidth="md" 
        sx={{ 
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column',
          pt: 10, // Add top padding to account for fixed header
          pb: 2,
          px: 2,
        }}
      >
        <Paper
          sx={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            p: 3,
            backgroundColor: 'white',
            borderRadius: 3,
            mb: 2,
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08)',
            border: 'none',
          }}
        >
          <MessageList 
            messages={messages} 
            onFeedback={handleFeedback} 
          />
          
          <MessageInput onSendMessage={handleSendMessage} />
        </Paper>
      </Container>

      {/* Floating Human Help Button - Bottom Right Corner */}
      <Box
        sx={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          zIndex: 1000,
        }}
      >
        <Button
          variant="contained"
          startIcon={<HeadsetMic />}
          onClick={handleHumanService}
          sx={{
            borderRadius: 3,
            px: 3,
            py: 1.5,
            fontSize: '0.875rem',
            textTransform: 'none',
            backgroundColor: '#1976D2',
            color: 'white',
            boxShadow: '0 4px 12px rgba(25, 118, 210, 0.3)',
            '&:hover': { 
              backgroundColor: '#1565C0',
              transform: 'translateY(-2px)',
              boxShadow: '0 6px 20px rgba(25, 118, 210, 0.4)',
            },
            transition: 'all 0.3s ease',
          }}
        >
          Get Human Help
        </Button>
      </Box>
    </Box>
  );
};

export default ChatPage;