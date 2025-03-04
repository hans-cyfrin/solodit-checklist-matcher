import React, { useState, useContext } from 'react';
import { Box, TextField, Button, Typography, CircularProgress, Grid, useTheme } from '@mui/material';
import axios from 'axios';

interface TextInputPanelProps {
  inputText: string;
  setInputText: (text: string) => void;
  inputUrl: string;
  setInputUrl: (url: string) => void;
  onMatch: () => void;
  isLoading: boolean;
}

const TextInputPanel: React.FC<TextInputPanelProps> = ({
  inputText,
  setInputText,
  inputUrl,
  setInputUrl,
  onMatch,
  isLoading,
}) => {
  const theme = useTheme();
  const [isLoadingUrl, setIsLoadingUrl] = useState(false);
  const [urlError, setUrlError] = useState<string | null>(null);

  // Validate URL
  const validateUrl = (url: string): boolean => {
    try {
      const parsedUrl = new URL(url);
      return parsedUrl.protocol === 'https:';
    } catch (e) {
      return false;
    }
  };

  // Handle URL input change
  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const url = e.target.value;
    setInputUrl(url);

    // Clear error when input is cleared
    if (!url) {
      setUrlError(null);
    }
    // Only validate non-empty URLs to avoid showing errors while typing
    else if (url.length > 8 && !validateUrl(url)) {
      setUrlError('Please enter a valid HTTPS URL');
    } else {
      setUrlError(null);
    }
  };

  // Handle URL load
  const handleLoadUrl = async () => {
    if (!inputUrl || !validateUrl(inputUrl)) {
      setUrlError('Please enter a valid HTTPS URL');
      return;
    }

    setIsLoadingUrl(true);
    setUrlError(null);

    try {
      // In a real app, this would be a backend call to fetch and parse content
      // For now, we'll simulate it with a delay
      const response = await axios.get(`https://api.allorigins.win/get?url=${encodeURIComponent(inputUrl)}`);

      if (response && response.data && response.data.contents) {
        try {
          // Extract text content from HTML (simplified)
          const parser = new DOMParser();
          const doc = parser.parseFromString(response.data.contents, 'text/html');

          // Get text from body, removing script and style elements
          const scripts = doc.querySelectorAll('script, style');
          scripts.forEach(script => script.remove());

          // Get text content
          let content = doc.body ? (doc.body.textContent || '') : '';

          // Clean up whitespace
          content = content.replace(/\s+/g, ' ').trim();

          // Limit length
          if (content.length > 1000) {
            content = content.substring(0, 1000) + '...';
          }

          setInputText(content);
        } catch (parseError) {
          console.error('Error parsing HTML:', parseError);
          setUrlError('Failed to parse content from URL');
        }
      } else {
        setUrlError('Failed to load content from URL');
      }
    } catch (error) {
      console.error('Error loading URL:', error);
      setUrlError('Failed to load content from URL');
    } finally {
      setIsLoadingUrl(false);
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Typography variant="h6" gutterBottom>
        Input
      </Typography>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12}>
          <TextField
            label="URL (optional)"
            fullWidth
            variant="outlined"
            value={inputUrl}
            onChange={handleUrlChange}
            placeholder="https://example.com/audit-report"
            error={!!urlError}
            helperText={urlError}
            sx={{ mb: 1 }}
          />
          <Button
            variant="outlined"
            onClick={handleLoadUrl}
            disabled={!inputUrl || isLoadingUrl || !!urlError}
            startIcon={isLoadingUrl ? <CircularProgress size={20} color="inherit" /> : null}
          >
            {isLoadingUrl ? 'Loading...' : 'Load Content'}
          </Button>
        </Grid>
      </Grid>

      <Typography variant="subtitle1" gutterBottom>
        Issue Description
      </Typography>
      
      <Box sx={{ flexGrow: 1, mb: 2 }}>
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Describe the security issue or vulnerability..."
          style={{ 
            width: '100%', 
            height: '100%', 
            padding: '12px',
            fontFamily: 'inherit',
            fontSize: 'inherit',
            border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.23)' : 'rgba(0, 0, 0, 0.23)'}`,
            borderRadius: '4px',
            resize: 'none',
            backgroundColor: theme.palette.mode === 'dark' ? theme.palette.background.paper : '#fff',
            color: theme.palette.text.primary
          }}
        />
      </Box>

      <Button
        variant="contained"
        color="primary"
        onClick={onMatch}
        disabled={isLoading || !inputText.trim()}
        startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : null}
        fullWidth
      >
        {isLoading ? 'Matching...' : 'Match with Checklist'}
      </Button>
    </Box>
  );
};

export default TextInputPanel;