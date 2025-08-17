import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  Drawer,
  Typography,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  TextField,
  Chip,
  Divider,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  InputAdornment,
  Tooltip,
} from '@mui/material';
import {
  Close,
  Search,
  Delete,
  History,
  Chat,
  FilterList,
  Clear,
  Language as LanguageIcon,
  Person,
} from '@mui/icons-material';
import { useConversationHistory } from '../contexts/ConversationHistoryContext';
import { useLanguage } from '../contexts/LanguageContext';
import { ConversationSummary, ConversationFilter } from '../types/Conversation';

interface ConversationHistoryPanelProps {
  open: boolean;
  onClose: () => void;
  onLoadConversation: (conversationId: string) => void;
  onConversationDeleted?: (deletedConversationId: string) => void;
  currentUsername: string;
}

const ConversationHistoryPanel: React.FC<ConversationHistoryPanelProps> = ({
  open,
  onClose,
  onLoadConversation,
  onConversationDeleted,
  currentUsername,
}) => {
  const { language } = useLanguage();
  const {
    getConversationSummaries,
    deleteConversation,
    setFilter,
    clearFilter,
    state,
  } = useConversationHistory();

  const [searchQuery, setSearchQuery] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [conversationToDelete, setConversationToDelete] = useState<string | null>(null);
  const [filterDialogOpen, setFilterDialogOpen] = useState(false);
  const [tempFilter, setTempFilter] = useState<ConversationFilter>({});

  // Language translations
  const translations = {
    en: {
      title: 'Conversation History',
      search: 'Search conversations...',
      noConversations: 'No conversations found',
      deleteTitle: 'Delete Conversation',
      deleteMessage: 'Are you sure you want to delete this conversation? This action cannot be undone.',
      delete: 'Delete',
      cancel: 'Cancel',
      filters: 'Filters',
      clearFilters: 'Clear Filters',
      applyFilters: 'Apply Filters',
      username: 'Username',
      language: 'Language',
      allLanguages: 'All Languages',
      english: 'English',
      japanese: 'Japanese',
      messageCount: 'messages',
      loadConversation: 'Load Conversation',
      deleteConversation: 'Delete Conversation',
    },
    ja: {
      title: '会話履歴',
      search: '会話を検索...',
      noConversations: '会話が見つかりません',
      deleteTitle: '会話を削除',
      deleteMessage: 'この会話を削除してもよろしいですか？この操作は元に戻せません。',
      delete: '削除',
      cancel: 'キャンセル',
      filters: 'フィルター',
      clearFilters: 'フィルターをクリア',
      applyFilters: 'フィルターを適用',
      username: 'ユーザー名',
      language: '言語',
      allLanguages: 'すべての言語',
      english: '英語',
      japanese: '日本語',
      messageCount: 'メッセージ',
      loadConversation: '会話を読み込む',
      deleteConversation: '会話を削除',
    }
  };

  const t = translations[language];

  // Get filtered conversations
  const conversations = useMemo(() => {
    let filtered = getConversationSummaries();
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(conv => 
        conv.title.toLowerCase().includes(query) ||
        conv.lastMessage?.toLowerCase().includes(query)
      );
    }
    
    // Debug: Log conversation IDs in the list
    console.log('📋 Conversation list IDs:', filtered.map(c => ({ id: c.id, title: c.title })));
    
    return filtered;
  }, [getConversationSummaries, searchQuery]);

  const handleSearch = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value);
  }, []);

  const handleDeleteClick = useCallback((conversationId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    console.log('🔍 Delete button clicked for conversation ID:', conversationId);
    setConversationToDelete(conversationId);
    setDeleteDialogOpen(true);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (conversationToDelete) {
      try {
        console.log('🗑️ Deleting conversation in history panel:', conversationToDelete);
        await deleteConversation(conversationToDelete);
        
        // Notify parent component that this conversation was deleted
        if (onConversationDeleted) {
          console.log('🔔 Calling onConversationDeleted callback with ID:', conversationToDelete);
          onConversationDeleted(conversationToDelete);
        } else {
          console.warn('⚠️ No onConversationDeleted callback provided');
        }
        
        setDeleteDialogOpen(false);
        setConversationToDelete(null);
        console.log('✅ Conversation deletion completed successfully');
      } catch (error) {
        console.error('❌ Failed to delete conversation:', error);
        // Keep dialog open to allow user to retry or cancel
        // Could add toast notification here for better UX
        alert('Failed to delete conversation. Please try again.');
      }
    }
  }, [conversationToDelete, deleteConversation, onConversationDeleted]);

  const handleDeleteCancel = useCallback(() => {
    setDeleteDialogOpen(false);
    setConversationToDelete(null);
  }, []);

  const handleConversationClick = useCallback((conversationId: string) => {
    onLoadConversation(conversationId);
    onClose();
  }, [onLoadConversation, onClose]);

  const handleFilterOpen = useCallback(() => {
    setTempFilter(state.filter);
    setFilterDialogOpen(true);
  }, [state.filter]);

  const handleFilterClose = useCallback(() => {
    setFilterDialogOpen(false);
    setTempFilter({});
  }, []);

  const handleFilterApply = useCallback(() => {
    setFilter(tempFilter);
    setFilterDialogOpen(false);
  }, [tempFilter, setFilter]);

  const handleFilterClear = useCallback(() => {
    clearFilter();
    setTempFilter({});
  }, [clearFilter]);

  const formatDate = useCallback((date: Date) => {
    return date.toLocaleDateString(language === 'ja' ? 'ja-JP' : 'en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }, [language]);

  const hasActiveFilters = useMemo(() => {
    return Object.keys(state.filter).length > 0;
  }, [state.filter]);

  return (
    <>
      <Drawer
        anchor="right"
        open={open}
        onClose={onClose}
        sx={{
          '& .MuiDrawer-paper': {
            width: 400,
            maxWidth: '90vw',
          },
        }}
      >
        <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
          {/* Header */}
          <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <History />
                {t.title}
              </Typography>
              <IconButton onClick={onClose}>
                <Close />
              </IconButton>
            </Box>

            {/* Search */}
            <TextField
              fullWidth
              placeholder={t.search}
              value={searchQuery}
              onChange={handleSearch}
              variant="outlined"
              size="small"
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
              sx={{ mb: 1 }}
            />

            {/* Filter controls */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Button
                startIcon={<FilterList />}
                onClick={handleFilterOpen}
                size="small"
                variant={hasActiveFilters ? 'contained' : 'outlined'}
                color={hasActiveFilters ? 'primary' : 'inherit'}
              >
                {t.filters}
              </Button>
              {hasActiveFilters && (
                <Button
                  startIcon={<Clear />}
                  onClick={handleFilterClear}
                  size="small"
                  color="inherit"
                >
                  {t.clearFilters}
                </Button>
              )}
            </Box>
          </Box>

          {/* Content */}
          <Box sx={{ flex: 1, overflow: 'auto' }}>
            {conversations.length === 0 ? (
              <Box sx={{ p: 3, textAlign: 'center', color: 'text.secondary' }}>
                <History sx={{ fontSize: 48, mb: 2, opacity: 0.5 }} />
                <Typography variant="body1">{t.noConversations}</Typography>
              </Box>
            ) : (
              <List>
                {conversations.map((conversation, index) => (
                  <React.Fragment key={conversation.id}>
                    <ListItem
                      component="div"
                      onClick={() => handleConversationClick(conversation.id)}
                      sx={{
                        cursor: 'pointer',
                        '&:hover': {
                          backgroundColor: 'action.hover',
                        },
                      }}
                    >
                      <Box sx={{ width: '100%' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Chat fontSize="small" color="action" />
                          <Typography
                            variant="subtitle2"
                            sx={{
                              fontWeight: 600,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              flex: 1,
                            }}
                          >
                            {conversation.title}
                          </Typography>
                          <Tooltip title={t.deleteConversation}>
                            <IconButton
                              size="small"
                              onClick={(e) => handleDeleteClick(conversation.id, e)}
                              sx={{ color: 'error.main' }}
                            >
                              <Delete fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                        
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Chip
                            icon={<Person />}
                            label={conversation.username}
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            icon={<LanguageIcon />}
                            label={conversation.language === 'ja' ? t.japanese : t.english}
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            label={`${conversation.messageCount} ${t.messageCount}`}
                            size="small"
                            variant="outlined"
                          />
                        </Box>

                        {conversation.lastMessage && (
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              mb: 1,
                            }}
                          >
                            {conversation.lastMessage}
                          </Typography>
                        )}

                        <Typography variant="caption" color="text.secondary">
                          {formatDate(conversation.updatedAt)}
                        </Typography>
                      </Box>
                    </ListItem>
                    {index < conversations.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            )}
          </Box>
        </Box>
      </Drawer>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{t.deleteTitle}</DialogTitle>
        <DialogContent>
          <Typography>{t.deleteMessage}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel}>{t.cancel}</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            {t.delete}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Filter Dialog */}
      <Dialog
        open={filterDialogOpen}
        onClose={handleFilterClose}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>{t.filters}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              fullWidth
              label={t.username}
              value={tempFilter.username || ''}
              onChange={(e) => setTempFilter(prev => ({ ...prev, username: e.target.value }))}
              variant="outlined"
            />
            
            <FormControl fullWidth>
              <InputLabel>{t.language}</InputLabel>
              <Select
                value={tempFilter.language || ''}
                label={t.language}
                onChange={(e) => setTempFilter(prev => ({ 
                  ...prev, 
                  language: e.target.value as 'en' | 'ja' | undefined 
                }))}
              >
                <MenuItem value="">{t.allLanguages}</MenuItem>
                <MenuItem value="en">{t.english}</MenuItem>
                <MenuItem value="ja">{t.japanese}</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleFilterClose}>{t.cancel}</Button>
          <Button onClick={handleFilterApply} variant="contained">
            {t.applyFilters}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default ConversationHistoryPanel;