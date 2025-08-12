/**
 * Data Migration Panel Component
 * Helps users manage the transition from localStorage to backend storage
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Storage,
  CloudSync,
  Warning,
  Delete,
  Refresh,
} from '@mui/icons-material';
import { useConversationHistory } from '../contexts/ConversationHistoryContext';
import { checkLocalStorageData, getLocalDataSummary, clearLocalStorageData, LocalStorageData } from '../utils/migrationUtils';

const DataMigrationPanel: React.FC = () => {
  const [localData, setLocalData] = useState<LocalStorageData>({ conversations: [], hasLocalData: false });
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const { state, clearLocalStorage, syncWithBackend } = useConversationHistory();

  useEffect(() => {
    // Check for localStorage data on mount
    const data = checkLocalStorageData();
    setLocalData(data);
  }, []);

  const handleClearLocalStorage = async () => {
    try {
      clearLocalStorage();
      clearLocalStorageData();
      setLocalData({ conversations: [], hasLocalData: false });
      setShowConfirmDialog(false);
      
      // Refresh the page to reload conversations from backend only
      window.location.reload();
    } catch (error) {
      console.error('Error clearing localStorage:', error);
      alert('Failed to clear localStorage');
    }
  };

  const handleSyncWithBackend = async () => {
    try {
      await syncWithBackend();
      alert('Successfully synced with backend!');
    } catch (error) {
      console.error('Error syncing with backend:', error);
      alert('Failed to sync with backend');
    }
  };

  const localDataSummary = getLocalDataSummary();
  const hasLocalStorageData = localData.hasLocalData;
  const backendConversationCount = state.conversations.length;

  if (!hasLocalStorageData && backendConversationCount === 0) {
    return null; // No data to migrate
  }

  return (
    <Box sx={{ mb: 3 }}>
      <Card sx={{ backgroundColor: '#fff3e0', border: '1px solid #ff9800' }}>
        <CardContent>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Storage />
            Data Storage Status
          </Typography>

          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>Current Status:</Typography>
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <Chip 
                label={`Backend: ${backendConversationCount} conversations`}
                color="primary" 
                icon={<CloudSync />}
              />
              {hasLocalStorageData && (
                <Chip 
                  label={`LocalStorage: ${localDataSummary.totalConversations} conversations`}
                  color="warning" 
                  icon={<Storage />}
                />
              )}
            </Box>
          </Box>

          {hasLocalStorageData && (
            <>
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  You have old conversation data in browser storage that may be mixing with backend data.
                  For the best experience, we recommend clearing the old local data.
                </Typography>
              </Alert>

              <Typography variant="subtitle2" sx={{ mb: 1 }}>localStorage Details:</Typography>
              <List dense sx={{ mb: 2 }}>
                <ListItem>
                  <ListItemText 
                    primary="Total Conversations" 
                    secondary={localDataSummary.totalConversations}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText 
                    primary="Total Messages" 
                    secondary={localDataSummary.totalMessages}
                  />
                </ListItem>
                {localDataSummary.oldestDate && (
                  <ListItem>
                    <ListItemText 
                      primary="Date Range" 
                      secondary={`${localDataSummary.oldestDate.toLocaleDateString()} - ${localDataSummary.newestDate?.toLocaleDateString()}`}
                    />
                  </ListItem>
                )}
              </List>
            </>
          )}

          <Divider sx={{ my: 2 }} />

          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Button
              variant="outlined"
              startIcon={<Refresh />}
              onClick={handleSyncWithBackend}
              size="small"
            >
              Refresh from Backend
            </Button>
            
            {hasLocalStorageData && (
              <Button
                variant="outlined"
                color="warning"
                startIcon={<Delete />}
                onClick={() => setShowConfirmDialog(true)}
                size="small"
              >
                Clear Browser Storage
              </Button>
            )}
          </Box>

          <Typography variant="caption" sx={{ display: 'block', mt: 2, color: 'text.secondary' }}>
            <strong>Note:</strong> New conversations are automatically saved to the backend database. 
            Browser storage is only used as a fallback for unauthenticated users.
          </Typography>
        </CardContent>
      </Card>

      {/* Confirmation Dialog */}
      <Dialog open={showConfirmDialog} onClose={() => setShowConfirmDialog(false)}>
        <DialogTitle>Clear Browser Storage</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to clear all conversation data from browser storage? 
            This will remove {localDataSummary.totalConversations} conversations and {localDataSummary.totalMessages} messages from your local browser.
          </Typography>
          <Alert severity="warning" sx={{ mt: 2 }}>
            This action cannot be undone. Only data from the backend database will remain.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowConfirmDialog(false)}>Cancel</Button>
          <Button onClick={handleClearLocalStorage} color="warning" variant="contained">
            Clear Storage
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DataMigrationPanel;