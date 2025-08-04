import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Box,
  Paper,
  Button,
  Typography,
  AppBar,
  Toolbar,
  Container,
  Chip,
  Avatar,
} from '@mui/material';
import { 
  SupportAgent, 
  AccountCircle, 
  ExitToApp, 
  HeadsetMic,
  History,
  Add
} from '@mui/icons-material';
import { Message } from '../types/Message';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { useToast } from './Toast';
import { storageUtils } from '../utils/storageUtils';
import { messageUtils } from '../utils/messageUtils';
import { chatService, ChatError } from '../services/chatService';
import { debounce } from '../utils/debounce';
import LanguageSelector from './LanguageSelector';
import ConversationHistoryPanel from './ConversationHistoryPanel';
import { useLanguage } from '../contexts/LanguageContext';
import { useConversationHistory } from '../contexts/ConversationHistoryContext';

interface ChatPageProps {
  username: string;
  onLogout: () => void;
}

const ChatPage: React.FC<ChatPageProps> = ({ username, onLogout }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [historyPanelOpen, setHistoryPanelOpen] = useState(false);
  const { showError, showSuccess } = useToast();
  const { language, setLanguage } = useLanguage();
  const { 
    saveConversation, 
    updateCurrentConversation, 
    loadConversation, 
    startNewConversation,
    state: historyState 
  } = useConversationHistory();

  // Language translations
  const translations = {
    en: {
      title: 'DataPro Support Chat',
      logout: 'Logout',
      humanHelp: 'Get Human Help',
      history: 'Conversation History',
      newConversation: 'New Chat',
      loadSuccess: 'Conversation loaded successfully!',
      loadError: 'Failed to load conversation'
    },
    ja: {
      title: 'DataProサポートチャット',
      logout: 'ログアウト',
      humanHelp: '人間のサポートを受ける',
      history: '会話履歴',
      newConversation: '新しいチャット',
      loadSuccess: '会話が正常に読み込まれました！',
      loadError: '会話の読み込みに失敗しました'
    }
  };

  const t = translations[language];

  // Debounce localStorage saves to improve performance
  const debouncedSaveMessages = useMemo(
    () => debounce(storageUtils.saveMessages, 500),
    []
  );

  // Load saved messages on component mount
  useEffect(() => {
    const savedMessages = storageUtils.getMessages();
    
    if (savedMessages.length > 0) {
      setMessages(savedMessages);
    } else {
      // No saved messages, start with welcome message
      const welcomeMessage = messageUtils.createWelcomeMessage(username, language);
      setMessages([welcomeMessage]);
    }
  }, [username, language]);

  // Save messages to localStorage whenever messages change (debounced)
  useEffect(() => {
    if (messages.length > 0) {
      debouncedSaveMessages(messages);
    }
  }, [messages, debouncedSaveMessages]);

  const handleSendMessage = useCallback(async (message: string, file?: File) => {
    if (!messageUtils.validateMessage(message, file)) return;

    // Add user message with sending status
    const userMessage = messageUtils.createMessage(message, 'user', file, 'sending');
    setMessages(prev => [...prev, userMessage]);

    try {
      // Update user message to sent status
      setMessages(prev => 
        messageUtils.updateMessageStatus(prev, userMessage.id, 'sent')
      );

      // Show typing indicator
      setIsTyping(true);

      // Generate bot response
      const response = await chatService.generateResponse(userMessage, language);
      
      // Hide typing indicator and add bot message
      setIsTyping(false);
      setMessages(prev => [...prev, response.message]);
      
    } catch (error) {
      setIsTyping(false);
      const chatError = error as ChatError;
      
      // Update user message to failed status
      setMessages(prev => 
        messageUtils.updateMessageStatus(prev, userMessage.id, 'failed', chatError.message)
      );
      
      showError(chatError.message);
      console.error('Error generating bot response:', error);
    }
  }, [showError, language]);

  const handleRetryMessage = useCallback(async (messageId: string) => {
    const message = messages.find(m => m.id === messageId);
    if (!message || !messageUtils.canRetryMessage(message)) return;

    // Increment retry count and set to sending
    setMessages(prev => messageUtils.incrementRetryCount(prev, messageId));

    try {
      setIsTyping(true);
      
      const response = await chatService.retryMessage(message, language, message.retryCount || 0);
      
      setIsTyping(false);
      
      // Update original message to sent status
      setMessages(prev => 
        messageUtils.updateMessageStatus(prev, messageId, 'sent')
      );
      
      // Add bot response
      setMessages(prev => [...prev, response.message]);
      
      showSuccess('Message sent successfully!');
      
    } catch (error) {
      setIsTyping(false);
      const chatError = error as ChatError;
      
      setMessages(prev => 
        messageUtils.updateMessageStatus(prev, messageId, 'failed', chatError.message)
      );
      
      showError(chatError.message);
    }
  }, [messages, showError, showSuccess, language]);

  const handleFeedback = useCallback((messageId: string, feedback: 'up' | 'down') => {
    setMessages(prev => messageUtils.updateMessageFeedback(prev, messageId, feedback));
  }, []);

  const handleHumanService = useCallback(() => {
    const serviceMessage = chatService.createHumanServiceMessage(language);
    setMessages(prev => [...prev, serviceMessage]);
  }, [language]);

  // Auto-save conversation whenever messages change (with meaningful content)
  useEffect(() => {
    if (messages.length > 1) { // More than just welcome message
      const autoSave = async () => {
        try {
          await updateCurrentConversation(messages, username, language);
        } catch (error) {
          console.error('Error auto-saving conversation:', error);
        }
      };
      
      // Debounce auto-save to avoid too frequent saves
      const timeoutId = setTimeout(autoSave, 2000); // Save 2 seconds after last message
      return () => clearTimeout(timeoutId);
    }
  }, [messages, username, language, updateCurrentConversation]);

  const handleLoadConversation = useCallback(async (conversationId: string) => {
    try {
      const conversation = await loadConversation(conversationId);
      if (conversation) {
        setMessages(conversation.messages);
        showSuccess(t.loadSuccess);
      }
    } catch (error) {
      showError(t.loadError);
      console.error('Error loading conversation:', error);
    }
  }, [loadConversation, showSuccess, showError, t]);

  const handleHistoryToggle = useCallback(() => {
    setHistoryPanelOpen(prev => !prev);
  }, []);

  const handleHistoryClose = useCallback(() => {
    setHistoryPanelOpen(false);
  }, []);

  const handleNewConversation = useCallback(() => {
    // Start new conversation (auto-save will handle saving current conversation)
    startNewConversation();
    const welcomeMessage = messageUtils.createWelcomeMessage(username, language);
    setMessages([welcomeMessage]);
  }, [startNewConversation, username, language]);

  const handleLogout = useCallback(() => {
    // Auto-save will handle saving current conversation
    onLogout();
  }, [onLogout]);



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
            {t.title}
          </Typography>
          
          {/* New Conversation Button */}
          <Button
            color="inherit"
            startIcon={<Add />}
            onClick={handleNewConversation}
            sx={{ mr: 1 }}
          >
            {t.newConversation}
          </Button>

          {/* History Button */}
          <Button
            color="inherit"
            startIcon={<History />}
            onClick={handleHistoryToggle}
            sx={{ mr: 1 }}
          >
            {t.history}
          </Button>

          {/* Language Selector */}
          <LanguageSelector
            currentLanguage={language}
            onLanguageChange={setLanguage}
            variant="header"
          />
          <Chip
            avatar={
              <Avatar sx={{ 
                backgroundColor: 'white !important',
                color: '#1565C0 !important',
                width: 24,
                height: 24,
              }}>
                <AccountCircle />
              </Avatar>
            }
            label={username}
            variant="outlined"
            sx={{ 
              color: 'white', 
              borderColor: 'white', 
              mr: 2,
            }}
          />
          
          <Button
            color="inherit"
            startIcon={<ExitToApp />}
            onClick={handleLogout}
          >
            {t.logout}
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
          height: 0, // Force height constraint in flexbox
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
            height: 0, // Force flexbox to constrain height
            minHeight: 400, // Minimum height for chat
          }}
        >
          <MessageList 
            messages={messages} 
            onFeedback={handleFeedback}
            onRetryMessage={handleRetryMessage}
            isTyping={isTyping}
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
          {t.humanHelp}
        </Button>
      </Box>

      {/* Conversation History Panel */}
      <ConversationHistoryPanel
        open={historyPanelOpen}
        onClose={handleHistoryClose}
        onLoadConversation={handleLoadConversation}
        currentUsername={username}
      />
    </Box>
  );
};

export default ChatPage;