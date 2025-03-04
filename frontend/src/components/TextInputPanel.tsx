import React, { useState } from 'react';
import { Box, TextField, Button, Typography, CircularProgress, Grid, Alert } from '@mui/material';
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
    <Box>
      <Typography variant="h6" gutterBottom>
        Input
      </Typography>

      <Grid container spacing={2}>
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
            sx={{ mb: 2 }}
          />
          <Button
            variant="outlined"
            onClick={handleLoadUrl}
            disabled={!inputUrl || isLoadingUrl || !!urlError}
            sx={{ mb: 2 }}
            startIcon={isLoadingUrl ? <CircularProgress size={20} color="inherit" /> : null}
          >
            {isLoadingUrl ? 'Loading...' : 'Load Content'}
          </Button>
        </Grid>

        <Grid item xs={12}>
          <TextField
            label="Issue Description"
            fullWidth
            multiline
            rows={6}
            variant="outlined"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Describe the security issue or vulnerability..."
            sx={{ mb: 2 }}
          />
        </Grid>

        <Grid item xs={12}>
          <Button
            variant="contained"
            color="primary"
            onClick={onMatch}
            disabled={isLoading || !inputText.trim()}
            startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : null}
          >
            {isLoading ? 'Matching...' : 'Match with Checklist'}
          </Button>
        </Grid>
      </Grid>
    </Box>
  );
};

export default TextInputPanel;