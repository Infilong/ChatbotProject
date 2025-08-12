/**
 * ConversationMigrationNotice Component
 * Helps users understand the transition from localStorage to backend storage
 */

import React, { useState } from 'react';
import {
  Box,
  Card,
  Typography,
  Button,
  Alert,
  AlertTitle,
  Collapse,
  IconButton,
} from '@mui/material';
import {
  CloudSync,
  Warning,
  Close,
  Refresh,
  DeleteOutline,
} from '@mui/icons-material';
import { useConversationHistory } from '../contexts/ConversationHistoryContext';

interface ConversationMigrationNoticeProps {
  onClose: () => void;
}

const ConversationMigrationNotice: React.FC<ConversationMigrationNoticeProps> = ({ onClose }) => {
  const [isLoading, setIsLoading] = useState(false);
  const { clearLocalStorage, syncWithBackend } = useConversationHistory();

  const handleClearLocalStorage = async () => {
    if (window.confirm('Are you sure you want to clear local conversation history? This action cannot be undone.')) {
      try {
        clearLocalStorage();
        alert('Local storage cleared successfully!');
        onClose();
      } catch (error) {
        console.error('Error clearing localStorage:', error);
        alert('Failed to clear local storage. Check console for details.');
      }
    }
  };

  const handleSyncWithBackend = async () => {
    setIsLoading(true);
    try {
      await syncWithBackend();
      alert('Successfully synced with backend!');
    } catch (error) {
      console.error('Error syncing with backend:', error);
      alert('Failed to sync with backend. Check console for details.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box sx={{ mb: 2 }}>
      <Alert severity="info" sx={{ backgroundColor: '#e3f2fd', border: '1px solid #2196f3' }}>
        <AlertTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CloudSync />
          Conversation History Update
          <IconButton size="small" onClick={onClose} sx={{ ml: 'auto' }}>
            <Close fontSize="small" />
          </IconButton>
        </AlertTitle>
        
        <Typography variant="body2" sx={{ mb: 2 }}>
          Your conversations are now stored securely in the backend database instead of browser storage.
          You may still see old conversations from local storage.
        </Typography>

        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button
            size="small"
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleSyncWithBackend}
            disabled={isLoading}
          >
            {isLoading ? 'Syncing...' : 'Sync with Backend'}
          </Button>
          
          <Button
            size="small"
            variant="outlined"
            color="warning"
            startIcon={<DeleteOutline />}
            onClick={handleClearLocalStorage}
          >
            Clear Local Data
          </Button>
        </Box>

        <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary' }}>
          <strong>Note:</strong> New conversations will automatically be saved to the backend.
          Local storage is only used as a fallback for unauthenticated users.
        </Typography>
      </Alert>
    </Box>
  );
};

export default ConversationMigrationNotice;