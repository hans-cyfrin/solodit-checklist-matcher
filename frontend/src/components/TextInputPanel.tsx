import React from 'react';
import { Box, TextField, Button, Typography, CircularProgress, Grid } from '@mui/material';

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
  // Handle URL load (in a real app, this would fetch content from the URL)
  const handleLoadUrl = async () => {
    if (!inputUrl) return;

    try {
      // This is a placeholder. In a real app, you would fetch the content from the URL
      // and set it as the input text.
      setInputText(`Content loaded from ${inputUrl}`);
    } catch (error) {
      console.error('Error loading URL:', error);
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
            onChange={(e) => setInputUrl(e.target.value)}
            placeholder="https://example.com/audit-report"
            sx={{ mb: 2 }}
          />
          <Button
            variant="outlined"
            onClick={handleLoadUrl}
            disabled={!inputUrl}
            sx={{ mb: 2 }}
          >
            Load Content
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