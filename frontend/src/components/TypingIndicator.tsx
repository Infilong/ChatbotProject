import React from 'react';
import {
  Box,
  Paper,
  Avatar,
  keyframes,
} from '@mui/material';
import { SupportAgent } from '@mui/icons-material';

const bounce = keyframes`
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-10px);
  }
`;

const TypingIndicator: React.FC = () => {
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'flex-start',
        mb: 2,
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 1,
          maxWidth: '70%',
        }}
      >
        <Avatar
          sx={{
            backgroundColor: '#26A69A',
            width: 32,
            height: 32,
            color: 'white',
          }}
        >
          <SupportAgent />
        </Avatar>
        
        <Paper
          sx={{
            p: 2,
            backgroundColor: 'white',
            borderRadius: 1,
            minWidth: 60,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 0.5,
          }}
        >
          {[0, 1, 2].map((index) => (
            <Box
              key={index}
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: '#1565C0',
                animation: `${bounce} 1.4s infinite ease-in-out`,
                animationDelay: `${index * 0.16}s`,
              }}
            />
          ))}
        </Paper>
      </Box>
    </Box>
  );
};

export default TypingIndicator;