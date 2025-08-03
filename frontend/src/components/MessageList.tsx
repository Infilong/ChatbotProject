import React, { useRef, useEffect, useMemo, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Avatar,
  IconButton,
  Stack,
  Chip,
  Tooltip,
} from '@mui/material';
import { 
  SupportAgent, 
  AccountCircle, 
  AttachFile, 
  ThumbUp, 
  ThumbDown,
  Refresh,
  Schedule,
  Error as ErrorIcon,
  CheckCircle,
} from '@mui/icons-material';
import { Message } from '../types/Message';
import TypingIndicator from './TypingIndicator';
import { throttle } from '../utils/debounce';

interface MessageListProps {
  messages: Message[];
  onFeedback: (messageId: string, feedback: 'up' | 'down') => void;
  onRetryMessage?: (messageId: string) => void;
  isTyping?: boolean;
}

const MessageList: React.FC<MessageListProps> = React.memo(({ 
  messages, 
  onFeedback, 
  onRetryMessage,
  isTyping = false 
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Throttle scroll to bottom to improve performance
  const scrollToBottom = useMemo(
    () => throttle(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100),
    []
  );

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Memoize utility functions to prevent unnecessary re-renders
  const formatTime = useCallback((timestamp: Date) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }, []);

  const getStatusIcon = useCallback((message: Message) => {
    switch (message.status) {
      case 'sending':
        return <Schedule fontSize="small" sx={{ color: 'text.secondary' }} />;
      case 'sent':
      case 'delivered':
        return <CheckCircle fontSize="small" sx={{ color: 'success.main' }} />;
      case 'failed':
        return <ErrorIcon fontSize="small" sx={{ color: 'error.main' }} />;
      default:
        return null;
    }
  }, []);

  const canRetry = useCallback((message: Message) => {
    return message.status === 'failed' && (message.retryCount || 0) < 3;
  }, []);

  return (
    <Box
      sx={{
        flex: 1,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        pb: 2,
      }}
    >
      {messages.map((message) => (
        <Box
          key={message.id}
          sx={{
            display: 'flex',
            justifyContent: message.sender === 'user' ? 'flex-end' : 'flex-start',
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 1,
              maxWidth: '70%',
              flexDirection: message.sender === 'user' ? 'row-reverse' : 'row',
            }}
          >
            <Avatar
              sx={{
                backgroundColor: message.sender === 'user' ? '#FFFFFF' : '#26A69A',
                width: 32,
                height: 32,
                color: message.sender === 'user' ? '#1565C0' : 'white',
                border: message.sender === 'user' ? '2px solid #1565C0' : 'none',
              }}
            >
              {message.sender === 'user' ? <AccountCircle /> : <SupportAgent />}
            </Avatar>
            <Box>
              <Paper
                sx={{
                  p: 2,
                  backgroundColor: message.sender === 'user' ? '#E3F2FD' : 'white',
                  borderRadius: 1,
                }}
              >
                <Typography variant="body1">
                  {message.text}
                </Typography>
                {message.file && (
                  <Box sx={{ mt: 1, p: 1, backgroundColor: '#F5F5F5', borderRadius: 1 }}>
                    <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <AttachFile fontSize="small" />
                      {message.file.name} ({(message.file.size / 1024).toFixed(1)} KB)
                    </Typography>
                  </Box>
                )}
              </Paper>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: message.sender === 'user' ? 'flex-end' : 'flex-start',
                  gap: 0.5,
                  mt: 0.5,
                }}
              >
                <Typography
                  variant="caption"
                  color="text.secondary"
                >
                  {formatTime(message.timestamp)}
                </Typography>
                
                {message.sender === 'user' && getStatusIcon(message)}
                
                {message.status === 'failed' && canRetry(message) && onRetryMessage && (
                  <Tooltip title="Retry sending message">
                    <IconButton
                      size="small"
                      onClick={() => onRetryMessage(message.id)}
                      sx={{ ml: 0.5 }}
                    >
                      <Refresh fontSize="small" />
                    </IconButton>
                  </Tooltip>
                )}
              </Box>
              
              {message.error && (
                <Chip
                  label={message.error}
                  size="small"
                  color="error"
                  variant="outlined"
                  sx={{ mt: 0.5, fontSize: '0.7rem' }}
                />
              )}
              
              {/* Feedback buttons for bot messages */}
              {message.sender === 'bot' && (
                <Stack direction="row" spacing={1} sx={{ mt: 1, alignItems: 'center' }}>
                  <IconButton
                    size="small"
                    onClick={() => onFeedback(message.id, 'up')}
                    sx={{
                      borderRadius: 2,
                      border: '1px solid',
                      borderColor: message.feedback === 'up' ? '#4CAF50' : '#E0E0E0',
                      backgroundColor: message.feedback === 'up' ? '#4CAF50' : 'transparent',
                      color: message.feedback === 'up' ? 'white' : 'text.secondary',
                      '&:hover': { 
                        borderColor: '#4CAF50',
                        backgroundColor: message.feedback === 'up' ? '#45A049' : 'rgba(76, 175, 80, 0.05)',
                      },
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <ThumbUp fontSize="small" />
                  </IconButton>
                  
                  <IconButton
                    size="small"
                    onClick={() => onFeedback(message.id, 'down')}
                    sx={{
                      borderRadius: 2,
                      border: '1px solid',
                      borderColor: message.feedback === 'down' ? '#F44336' : '#E0E0E0',
                      backgroundColor: message.feedback === 'down' ? '#F44336' : 'transparent',
                      color: message.feedback === 'down' ? 'white' : 'text.secondary',
                      '&:hover': { 
                        borderColor: '#F44336',
                        backgroundColor: message.feedback === 'down' ? '#E53935' : 'rgba(244, 67, 54, 0.05)',
                      },
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <ThumbDown fontSize="small" />
                  </IconButton>
                </Stack>
              )}
            </Box>
          </Box>
        </Box>
      ))}
      
      {isTyping && <TypingIndicator />}
      
      <div ref={messagesEndRef} />
    </Box>
  );
});

MessageList.displayName = 'MessageList';

export default MessageList;