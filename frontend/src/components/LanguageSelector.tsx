import React from 'react';
import {
  Box,
  IconButton,
  Menu,
  MenuItem,
  Typography,
  Tooltip,
} from '@mui/material';
import { Language } from '@mui/icons-material';

export type LanguageType = 'en' | 'ja';

interface Language {
  code: LanguageType;
  name: string;
  flag: string;
}

const languages: Language[] = [
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'ja', name: '日本語', flag: '🇯🇵' },
];

interface LanguageSelectorProps {
  currentLanguage: LanguageType;
  onLanguageChange: (language: LanguageType) => void;
  variant?: 'header' | 'page';
}

const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  currentLanguage,
  onLanguageChange,
  variant = 'header'
}) => {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLanguageSelect = (language: LanguageType) => {
    onLanguageChange(language);
    handleClose();
  };

  const currentLang = languages.find(lang => lang.code === currentLanguage);

  return (
    <Box>
      <Tooltip title="Select Language">
        <IconButton
          onClick={handleClick}
          sx={{
            color: variant === 'header' ? 'white' : 'inherit',
            '&:hover': {
              backgroundColor: variant === 'header' 
                ? 'rgba(255, 255, 255, 0.1)' 
                : 'rgba(0, 0, 0, 0.04)',
            },
          }}
        >
          <Language />
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        MenuListProps={{
          'aria-labelledby': 'language-button',
        }}
        sx={{
          '& .MuiPaper-root': {
            minWidth: 140,
            borderRadius: 2,
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          },
        }}
      >
        {languages.map((language) => (
          <MenuItem
            key={language.code}
            onClick={() => handleLanguageSelect(language.code)}
            selected={language.code === currentLanguage}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              py: 1.5,
              '&.Mui-selected': {
                backgroundColor: '#E3F2FD',
                '&:hover': {
                  backgroundColor: '#BBDEFB',
                },
              },
            }}
          >
            <Typography sx={{ fontSize: '1.2rem' }}>
              {language.flag}
            </Typography>
            <Typography variant="body2">
              {language.name}
            </Typography>
          </MenuItem>
        ))}
      </Menu>
    </Box>
  );
};

export default LanguageSelector;