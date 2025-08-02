import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Box,
  IconButton,
} from '@mui/material';

interface EmojiPickerProps {
  open: boolean;
  onClose: () => void;
  onEmojiSelect: (emoji: string) => void;
}

const EmojiPicker: React.FC<EmojiPickerProps> = ({ open, onClose, onEmojiSelect }) => {
  const emojis = [
    '😊', '😂', '😍', '🤔', '👍', '👎', '❤️', '🎉', '🔥', '💯', 
    '🙏', '🤝', '👋', '✨', '💡', '📝', '🎯', '🚀', '⭐', '💪'
  ];

  const handleEmojiClick = (emoji: string) => {
    onEmojiSelect(emoji);
    onClose();
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="sm"
      PaperProps={{
        sx: {
          borderRadius: 3,
          p: 1,
        }
      }}
    >
      <DialogTitle sx={{ pb: 1, textAlign: 'center' }}>
        Choose an Emoji
      </DialogTitle>
      <DialogContent>
        <Box 
          sx={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(5, 1fr)', 
            gap: 1, 
            minWidth: 280,
            p: 1 
          }}
        >
          {emojis.map((emoji, index) => (
            <IconButton
              key={index}
              onClick={() => handleEmojiClick(emoji)}
              sx={{
                aspectRatio: '1',
                fontSize: '1.5rem',
                borderRadius: 2,
                '&:hover': {
                  backgroundColor: 'rgba(21, 101, 192, 0.1)',
                  transform: 'scale(1.1)',
                },
                transition: 'all 0.2s ease',
              }}
            >
              {emoji}
            </IconButton>
          ))}
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default EmojiPicker;