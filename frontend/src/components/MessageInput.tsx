import React, { useState, useRef, useCallback } from 'react';
import {
  Box,
  TextField,
  Button,
  IconButton,
  Typography,
} from '@mui/material';
import { 
  Send, 
  EmojiEmotions, 
  AttachFile,
} from '@mui/icons-material';
import EmojiPicker from './EmojiPicker';
import { useLanguage } from '../contexts/LanguageContext';

interface MessageInputProps {
  onSendMessage: (message: string, file?: File) => void;
  disabled?: boolean;
}

const MessageInput: React.FC<MessageInputProps> = React.memo(({ onSendMessage, disabled = false }) => {
  const [inputMessage, setInputMessage] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [emojiPickerOpen, setEmojiPickerOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { language } = useLanguage();

  // Language translations
  const translations = {
    en: {
      placeholder: "Type your message here...",
      selected: "Selected:",
      kb: "KB"
    },
    ja: {
      placeholder: "メッセージを入力してください...",
      selected: "選択済み:",
      kb: "KB"
    }
  };

  const t = translations[language];

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    
    if (!inputMessage.trim() && !selectedFile) return;
    if (disabled) return; // Prevent submission when disabled

    onSendMessage(inputMessage, selectedFile || undefined);
    setInputMessage('');
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [inputMessage, selectedFile, onSendMessage, disabled]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  }, []);

  const handleEmojiSelect = useCallback((emoji: string) => {
    setInputMessage(prev => prev + emoji);
  }, []);

  const clearSelectedFile = useCallback(() => {
    setSelectedFile(null);
  }, []);

  const toggleEmojiPicker = useCallback(() => {
    setEmojiPickerOpen(prev => !prev);
  }, []);

  const closeEmojiPicker = useCallback(() => {
    setEmojiPickerOpen(false);
  }, []);

  return (
    <>
      <form onSubmit={handleSubmit}>
        {/* File preview */}
        {selectedFile && (
          <Box sx={{ mb: 1, p: 1, backgroundColor: '#E3F2FD', borderRadius: 1 }}>
            <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <AttachFile fontSize="small" />
              {t.selected} {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} {t.kb})
              <IconButton size="small" onClick={clearSelectedFile}>
                ✕
              </IconButton>
            </Typography>
          </Box>
        )}
        
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
          {/* Emoji Picker Button */}
          <IconButton
            onClick={toggleEmojiPicker}
            disabled={disabled}
            sx={{
              color: disabled ? '#ccc' : '#1565C0',
              borderRadius: 2,
              '&:hover': disabled ? {} : { 
                backgroundColor: 'rgba(21, 101, 192, 0.1)',
                transform: 'scale(1.05)',
              },
              transition: 'all 0.2s ease',
            }}
          >
            <EmojiEmotions />
          </IconButton>
          
          <TextField
            fullWidth
            multiline
            maxRows={4}
            placeholder={t.placeholder}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            variant="outlined"
            disabled={disabled}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 3,
              },
            }}
          />
          
          {/* File Attachment */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            style={{ display: 'none' }}
            accept=".jpg,.jpeg,.png,.webp,.gif,.svg,.py,.js,.ts,.html,.css,.json,.md,.csv,.txt,.pdf,.docx,.pptx,.rtf"
          />
          <IconButton
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            sx={{
              color: disabled ? '#ccc' : '#1565C0',
              '&:hover': disabled ? {} : { backgroundColor: 'rgba(21, 101, 192, 0.1)' },
            }}
          >
            <AttachFile />
          </IconButton>
          
          <Button
            type="submit"
            variant="contained"
            disabled={disabled}
            sx={{
              minWidth: 48,
              height: 48,
              borderRadius: 3,
              backgroundColor: disabled ? '#f5f5f5' : 'white',
              color: disabled ? '#ccc' : '#1565C0',
              border: disabled ? '2px solid #e0e0e0' : '2px solid #1565C0',
              '&:hover': disabled ? {} : {
                backgroundColor: '#1565C0',
                color: 'white',
                transform: 'translateY(-2px)',
                boxShadow: '0 4px 15px rgba(21, 101, 192, 0.3)',
              },
              '&:disabled': {
                backgroundColor: '#f5f5f5',
                color: '#ccc',
                border: '2px solid #e0e0e0',
              },
            }}
          >
            <Send />
          </Button>
        </Box>
      </form>

      <EmojiPicker
        open={emojiPickerOpen}
        onClose={closeEmojiPicker}
        onEmojiSelect={handleEmojiSelect}
      />
    </>
  );
});

MessageInput.displayName = 'MessageInput';

export default MessageInput;