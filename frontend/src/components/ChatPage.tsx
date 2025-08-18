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
    loadConversation, 
    startNewConversation,
    setCurrentConversation,
    refreshConversations
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
    // Restore conversation ID from localStorage if available
    chatService.restoreConversationFromStorage();
    
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
      const previousConversationId = chatService.getCurrentConversationId();
      const response = await chatService.generateResponse(userMessage, language, {});
      const newConversationId = chatService.getCurrentConversationId();
      
      // Check if a new conversation was created (conversation ID changed from null to a value)
      const isNewConversation = !previousConversationId && newConversationId;
      
      // Hide typing indicator and add bot message
      setIsTyping(false);
      setMessages(prev => [...prev, response.message]);
      
      // If a new conversation was created, immediately refresh the conversation history
      if (isNewConversation) {
        console.log('🆕 New conversation detected! Refreshing conversation history immediately');
        console.log('  - Previous conversation ID:', previousConversationId);
        console.log('  - New conversation ID:', newConversationId);
        try {
          await refreshConversations();
          console.log('✅ Conversation history refreshed successfully');
        } catch (error) {
          console.error('Failed to refresh conversation history:', error);
        }
      }
      
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
  }, [showError, language, refreshConversations]);

  const handleRetryMessage = useCallback(async (messageId: string) => {
    const message = messages.find(m => m.id === messageId);
    if (!message || !messageUtils.canRetryMessage(message)) return;

    // Increment retry count and set to sending
    setMessages(prev => messageUtils.incrementRetryCount(prev, messageId));

    try {
      setIsTyping(true);
      
      const previousConversationId = chatService.getCurrentConversationId();
      const response = await chatService.retryMessage(message, language, {}, message.retryCount || 0);
      const newConversationId = chatService.getCurrentConversationId();
      
      // Check if a new conversation was created during retry
      const isNewConversation = !previousConversationId && newConversationId;
      
      setIsTyping(false);
      
      // Update original message to sent status
      setMessages(prev => 
        messageUtils.updateMessageStatus(prev, messageId, 'sent')
      );
      
      // Add bot response
      setMessages(prev => [...prev, response.message]);
      
      // If a new conversation was created, immediately refresh the conversation history
      if (isNewConversation) {
        console.log('🆕 New conversation detected during retry! Refreshing conversation history');
        try {
          await refreshConversations();
          console.log('✅ Conversation history refreshed after retry');
        } catch (error) {
          console.error('Failed to refresh conversation history after retry:', error);
        }
      }
      
      showSuccess('Message sent successfully!');
      
    } catch (error) {
      setIsTyping(false);
      const chatError = error as ChatError;
      
      setMessages(prev => 
        messageUtils.updateMessageStatus(prev, messageId, 'failed', chatError.message)
      );
      
      showError(chatError.message);
    }
  }, [messages, showError, showSuccess, language, refreshConversations]);

  const handleFeedback = useCallback(async (messageId: string, feedback: 'up' | 'down') => {
    // Update local state immediately for responsive UI
    setMessages(prev => messageUtils.updateMessageFeedback(prev, messageId, feedback));
    
    try {
      // Convert frontend feedback to backend format
      const backendFeedback = feedback === 'up' ? 'positive' : 'negative';
      
      // Submit feedback to backend API
      await chatService.submitFeedback(messageId, backendFeedback);
      
      console.log(`✅ Feedback submitted: ${messageId} -> ${backendFeedback}`);
    } catch (error) {
      console.error('Failed to submit feedback to backend:', error);
      showError('Failed to submit feedback. Please try again.');
    }
  }, [showError]);

  const handleHumanService = useCallback(() => {
    const serviceMessage = chatService.createHumanServiceMessage(language);
    setMessages(prev => [...prev, serviceMessage]);
  }, [language]);

  // Sync conversation ID with ConversationHistory context whenever messages change
  useEffect(() => {
    if (messages.length > 1) { // More than just welcome message
      const syncConversation = async () => {
        try {
          // Get the current conversation ID from chatService
          const currentConversationId = chatService.getCurrentConversationId();
          
          if (currentConversationId) {
            // If chatService has a conversation ID, sync it with the context
            setCurrentConversation(currentConversationId);
            console.log('Synced conversation ID with context:', currentConversationId);
          } else {
            console.log('No conversation ID from chatService yet');
          }
        } catch (error) {
          console.error('Error syncing conversation:', error);
        }
      };
      
      // Debounce sync to avoid too frequent updates
      const timeoutId = setTimeout(syncConversation, 1000); // Sync 1 second after last message
      return () => clearTimeout(timeoutId);
    }
  }, [messages, setCurrentConversation]);

  const handleLoadConversation = useCallback(async (conversationId: string) => {
    try {
      const conversation = await loadConversation(conversationId);
      if (conversation) {
        setMessages(conversation.messages);
        
        // Sync the conversation ID with chatService
        chatService.setCurrentConversationId(conversationId);
        
        console.log('📂 Loaded conversation and synced with chatService:', conversationId);
        console.log('📂 ChatService now stores conversation ID:', chatService.getCurrentConversationId());
        showSuccess(t.loadSuccess);
      }
    } catch (error) {
      showError(t.loadError);
      console.error('Error loading conversation:', error);
    }
  }, [loadConversation, showSuccess, showError, t]);

  const handleConversationDeleted = useCallback(async (deletedConversationId: string) => {
    // Check if the deleted conversation is the currently active one
    const currentConversationId = chatService.getCurrentConversationId();
    
    console.log('🔍 Conversation deleted callback triggered:');
    console.log('  - Deleted conversation ID:', deletedConversationId);
    console.log('  - Current conversation ID:', currentConversationId);
    console.log('  - IDs match:', currentConversationId === deletedConversationId);
    
    if (currentConversationId === deletedConversationId) {
      console.log('🧹 Clearing chat window - IDs match!');
      
      // Clear the current conversation and start fresh
      setMessages([]);
      chatService.setCurrentConversationId(null);
      
      // CRITICAL: Clear localStorage cache to prevent restoration on page refresh
      try {
        localStorage.removeItem('chatMessages');
        localStorage.removeItem('currentConversationId');
        console.log('🧹 Cleared localStorage cache: chatMessages, currentConversationId');
      } catch (error) {
        console.error('Failed to clear localStorage cache:', error);
      }
      
      // Start a new conversation
      startNewConversation();
      
      // Clear the chat service conversation ID
      await chatService.startNewConversation();
      
      // Ensure context is synchronized for new conversation  
      setCurrentConversation(null);
      
      // Add welcome message for new conversation
      const welcomeMessage = messageUtils.createWelcomeMessage(username, language);
      setMessages([welcomeMessage]);
      
      console.log('✅ Chat window cleared, localStorage cleared, new conversation started with welcome message');
    } else {
      console.log('ℹ️ Not clearing chat window - different conversation was deleted');
    }
  }, [startNewConversation, setCurrentConversation, username, language]);

  const handleHistoryToggle = useCallback(() => {
    setHistoryPanelOpen(prev => !prev);
  }, []);

  const handleHistoryClose = useCallback(() => {
    setHistoryPanelOpen(false);
  }, []);

  const handleNewConversation = useCallback(async () => {
    // Start new conversation (auto-save will handle saving current conversation)
    startNewConversation();
    
    // Clear the chat service conversation ID
    await chatService.startNewConversation();
    
    // Ensure both systems are synchronized for new conversation
    setCurrentConversation(null);
    
    const welcomeMessage = messageUtils.createWelcomeMessage(username, language);
    setMessages([welcomeMessage]);
  }, [startNewConversation, setCurrentConversation, username, language]);

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
        <Toolbar sx={{ minHeight: { xs: 56, sm: 64 }, px: { xs: 1, sm: 3 } }}>
          <SupportAgent sx={{ mr: { xs: 1, sm: 2 } }} />
          <Typography 
            variant="h6" 
            component="div" 
            sx={{ 
              flexGrow: 1,
              fontSize: { xs: '1rem', sm: '1.25rem' }, // Smaller title on mobile
              display: { xs: 'none', sm: 'block' }, // Hide full title on mobile
            }}
          >
            {t.title}
          </Typography>
          <Typography 
            variant="h6" 
            component="div" 
            sx={{ 
              flexGrow: 1,
              fontSize: '1rem',
              display: { xs: 'block', sm: 'none' }, // Show short title on mobile
            }}
          >
            DataPro
          </Typography>
          
          {/* Mobile: Icon-only buttons, Desktop: Full buttons */}
          
          {/* New Conversation Button */}
          <Button
            color="inherit"
            onClick={handleNewConversation}
            sx={{ 
              mr: { xs: 0.5, sm: 1 },
              minWidth: { xs: 40, sm: 'auto' },
              px: { xs: 1, sm: 2 },
            }}
          >
            <Box sx={{ display: { xs: 'none', sm: 'flex' }, alignItems: 'center', gap: 1 }}>
              <Add />
              {t.newConversation}
            </Box>
            <Box sx={{ display: { xs: 'flex', sm: 'none' } }}>
              <Add />
            </Box>
          </Button>

          {/* History Button */}
          <Button
            color="inherit"
            onClick={handleHistoryToggle}
            sx={{ 
              mr: { xs: 0.5, sm: 1 },
              minWidth: { xs: 40, sm: 'auto' },
              px: { xs: 1, sm: 2 },
            }}
          >
            <Box sx={{ display: { xs: 'none', sm: 'flex' }, alignItems: 'center', gap: 1 }}>
              <History />
              {t.history}
            </Box>
            <Box sx={{ display: { xs: 'flex', sm: 'none' } }}>
              <History />
            </Box>
          </Button>

          {/* Human Help Button */}
          <Button
            color="inherit"
            onClick={handleHumanService}
            sx={{ 
              mr: { xs: 0.5, sm: 1 },
              minWidth: { xs: 40, sm: 'auto' },
              px: { xs: 1, sm: 2 },
            }}
          >
            <Box sx={{ display: { xs: 'none', sm: 'flex' }, alignItems: 'center', gap: 1 }}>
              <HeadsetMic />
              {t.humanHelp}
            </Box>
            <Box sx={{ display: { xs: 'flex', sm: 'none' } }}>
              <HeadsetMic />
            </Box>
          </Button>

          {/* Language Selector */}
          <LanguageSelector
            currentLanguage={language}
            onLanguageChange={setLanguage}
            variant="header"
          />
          
          {/* User Avatar - Raw avatar on mobile, chip container on desktop */}
          <Box sx={{ mr: { xs: 0.5, sm: 2 } }}>
            {/* Mobile: Just the raw Avatar (no chip container) */}
            <Avatar 
              sx={{ 
                display: { xs: 'flex', sm: 'none' },
                backgroundColor: 'white !important',
                color: '#1565C0 !important',
                width: 24,
                height: 24,
              }}
            >
              <AccountCircle />
            </Avatar>
            
            {/* Desktop: Full Chip container with avatar + username */}
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
                display: { xs: 'none', sm: 'flex' },
                color: 'white', 
                borderColor: 'white',
              }}
            />
          </Box>
          
          {/* Logout Button */}
          <Button
            color="inherit"
            onClick={handleLogout}
            sx={{ 
              minWidth: { xs: 40, sm: 'auto' },
              px: { xs: 1, sm: 2 },
            }}
          >
            <Box sx={{ display: { xs: 'none', sm: 'flex' }, alignItems: 'center', gap: 1 }}>
              <ExitToApp />
              {t.logout}
            </Box>
            <Box sx={{ display: { xs: 'flex', sm: 'none' } }}>
              <ExitToApp />
            </Box>
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
          pt: { xs: 9, sm: 14, md: 12 }, // Spacing: 72px mobile, 112px tablet (labels), 96px desktop
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


      {/* Conversation History Panel */}
      <ConversationHistoryPanel
        open={historyPanelOpen}
        onClose={handleHistoryClose}
        onLoadConversation={handleLoadConversation}
        onConversationDeleted={handleConversationDeleted}
        currentUsername={username}
      />
    </Box>
  );
};

export default ChatPage;