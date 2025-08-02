import React, { useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Avatar,
  IconButton,
  Stack,
} from '@mui/material';
import { 
  SupportAgent, 
  AccountCircle, 
  AttachFile, 
  ThumbUp, 
  ThumbDown,
} from '@mui/icons-material';
import { Message } from '../types/Message';

interface MessageListProps {
  messages: Message[];
  onFeedback: (messageId: string, feedback: 'up' | 'down') => void;
}

const MessageList: React.FC<MessageListProps> = ({ messages, onFeedback }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const formatTime = (timestamp: Date) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

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
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{
                  display: 'block',
                  mt: 0.5,
                  textAlign: message.sender === 'user' ? 'right' : 'left',
                }}
              >
                {formatTime(message.timestamp)}
              </Typography>
              
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
      <div ref={messagesEndRef} />
    </Box>
  );
};

export default MessageList;