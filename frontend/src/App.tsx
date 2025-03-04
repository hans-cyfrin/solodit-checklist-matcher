import React, { useState, useMemo } from 'react';
import {
  Container,
  Box,
  Typography,
  Paper,
  AppBar,
  Toolbar,
  Button,
  Snackbar,
  Alert,
  CircularProgress,
  Backdrop,
  IconButton,
  Grid,
  Tooltip,
  ThemeProvider,
  CssBaseline,
  Switch,
  FormControlLabel
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import FavoriteIcon from '@mui/icons-material/Favorite';
import { useQuery, useMutation, QueryClient, QueryClientProvider } from 'react-query';
import axios from 'axios';
import { createTheme } from '@mui/material/styles';

import TextInputPanel from './components/TextInputPanel';
import MatchResults from './components/MatchResults';
import PendingChanges from './components/PendingChanges';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

// API base URL
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// Types
export interface ChecklistItem {
  id: string;
  category: string;
  question: string;
  description: string;
  remediation: string;
  references: string[];
  score?: number;
}

export interface PendingChange {
  change_id: number;
  checklist_item_id: string;
  source_url: string;
  status: string;
  created_at: string;
}

export interface MatchResult {
  matches: ChecklistItem[];
  input_text: string;
  input_url?: string;
  preprocessed_text?: string;
  preprocessing_applied?: boolean;
}

// Error handling wrapper for API calls
const safeApiCall = async (apiCall: () => Promise<any>) => {
  try {
    return await apiCall();
  } catch (error) {
    console.error('API call error:', error);
    // Safely handle the error without accessing properties that might not exist
    if (error && typeof error === 'object') {
      return { error: true, message: error.toString() };
    }
    return { error: true, message: 'An unknown error occurred' };
  }
};

// Main App component
function AppContent() {
  // Theme state
  const [mode, setMode] = useState<'light' | 'dark'>('light');
  
  // Create theme based on mode
  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode,
          primary: {
            main: '#1976d2',
          },
          secondary: {
            main: '#dc004e',
          },
          background: {
            default: mode === 'light' ? '#f5f5f5' : '#121212',
            paper: mode === 'light' ? '#ffffff' : '#1e1e1e',
          },
        },
      }),
    [mode],
  );

  // Toggle theme
  const toggleTheme = () => {
    setMode((prevMode) => (prevMode === 'light' ? 'dark' : 'light'));
  };

  // State
  const [inputText, setInputText] = useState('');
  const [inputUrl, setInputUrl] = useState('');
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [matchResults, setMatchResults] = useState<MatchResult | null>(null);
  const [activeTab, setActiveTab] = useState<'matcher' | 'pending'>('matcher');
  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });
  const [prResult, setPrResult] = useState<any>(null);

  // Close notification
  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false });
  };

  // Show notification
  const showNotification = (message: string, severity: 'success' | 'error' | 'info' | 'warning') => {
    setNotification({
      open: true,
      message,
      severity,
    });
  };

  // Fetch checklist
  const {
    data: checklist,
    isLoading: isLoadingChecklist,
    isError: isChecklistError,
    refetch: refetchChecklist
  } = useQuery<ChecklistItem[]>('checklist', async () => {
    try {
      const response = await safeApiCall(() => axios.get(`${API_BASE_URL}/checklist`));

      // Check if the response contains an error
      if (response && response.error) {
        showNotification('Failed to load checklist. Please try again later.', 'error');
        return [];
      }

      // Ensure response.data exists and has the expected structure
      if (response && response.data && Array.isArray(response.data)) {
        return response.data;
      } else {
        showNotification('Received invalid checklist data from server.', 'error');
        return [];
      }
    } catch (error) {
      console.error('Error fetching checklist:', error);
      showNotification('Failed to load checklist. Please try again later.', 'error');
      return [];
    }
  });

  // Fetch pending changes
  const {
    data: pendingChanges,
    isLoading: isLoadingPendingChanges,
    isError: isPendingChangesError,
    refetch: refetchPendingChanges
  } = useQuery<PendingChange[]>('pendingChanges', async () => {
    try {
      const response = await safeApiCall(() => axios.get(`${API_BASE_URL}/pending-changes`));

      // Check if the response contains an error
      if (response && response.error) {
        showNotification('Failed to load pending changes. Please try again later.', 'error');
        return [];
      }

      // Ensure response.data exists and has the expected structure
      if (response && response.data && Array.isArray(response.data)) {
        return response.data;
      } else {
        showNotification('Received invalid pending changes data from server.', 'error');
        return [];
      }
    } catch (error) {
      console.error('Error fetching pending changes:', error);
      showNotification('Failed to load pending changes. Please try again later.', 'error');
      return [];
    }
  });

  // Match text mutation
  const matchMutation = useMutation(async () => {
    try {
      const response = await safeApiCall(() => axios.post(`${API_BASE_URL}/match`, {
        text: inputText,
        url: inputUrl || undefined,
      }));

      // Check if the response contains an error
      if (response && response.error) {
        showNotification('Failed to match text. Please try again later.', 'error');
        return;
      }

      // Ensure response.data exists and has the expected structure
      if (response && response.data) {
        setMatchResults(response.data);

        if (response.data.matches && response.data.matches.length === 0) {
          showNotification('No matching checklist items found. Try a different description.', 'info');
        } else if (response.data.matches) {
          showNotification(`Found ${response.data.matches.length} matching checklist items.`, 'success');
        }
      } else {
        showNotification('Received invalid response from server.', 'error');
      }

      return response;
    } catch (error) {
      console.error('Error matching text:', error);
      showNotification('Failed to match text. Please try again later.', 'error');
      throw error;
    }
  });

  // Propose reference mutation
  const proposeReferenceMutation = useMutation(async () => {
    try {
      const changes = selectedItems.map(itemId => ({
        checklist_item_id: itemId,
        source_url: inputUrl
      }));

      const response = await safeApiCall(() => axios.post(`${API_BASE_URL}/propose-reference`, changes));

      // Check if the response contains an error
      if (response && response.error) {
        showNotification('Failed to propose reference. Please try again later.', 'error');
        return;
      }

      showNotification('Reference proposed successfully!', 'success');
      setSelectedItems([]);

      return response;
    } catch (error) {
      console.error('Error proposing reference:', error);
      showNotification('Failed to propose reference. Please try again later.', 'error');
      throw error;
    }
  }, {
    onSuccess: () => {
      refetchPendingChanges();
    }
  });

  // Create PR mutation
  const createPrMutation = useMutation(async () => {
    try {
      const response = await safeApiCall(() => axios.post(`${API_BASE_URL}/create-pr`));

      // Check if the response contains an error
      if (response && response.error) {
        showNotification('Failed to create PR. Please try again later.', 'error');
        return;
      }

      // Ensure response.data exists and has the expected structure
      if (response && response.data) {
        setPrResult(response.data);
        showNotification(`PR #${response.data.pr_number} created successfully!`, 'success');
      } else {
        showNotification('Received invalid response from server.', 'error');
      }

      return response;
    } catch (error) {
      console.error('Error creating PR:', error);
      showNotification('Failed to create PR. Please try again later.', 'error');
      throw error;
    }
  }, {
    onSuccess: () => {
      refetchPendingChanges();
    }
  });

  // Delete pending change mutation
  const deletePendingChangeMutation = useMutation(
    async (changeId: number) => {
      try {
        const response = await safeApiCall(() => axios.delete(`${API_BASE_URL}/pending-changes/${changeId}`));

        // Check if the response contains an error
        if (response && response.error) {
          showNotification('Failed to delete pending change. Please try again.', 'error');
          return;
        }

        showNotification('Pending change deleted successfully.', 'success');
        return response;
      } catch (error) {
        console.error('Error deleting pending change:', error);
        showNotification('Failed to delete pending change. Please try again.', 'error');
        throw error;
      }
    },
    {
      onSuccess: () => {
        refetchPendingChanges();
      }
    }
  );

  // Resync checklist mutation
  const resyncMutation = useMutation(async () => {
    try {
      const response = await safeApiCall(() => axios.post(`${API_BASE_URL}/resync`));

      // Check if the response contains an error
      if (response && response.error) {
        showNotification('Failed to resync checklist. Please try again later.', 'error');
        return;
      }

      showNotification('Checklist resync started. This may take a moment.', 'info');

      // Wait a bit and then refetch the checklist
      setTimeout(() => {
        refetchChecklist();
        showNotification('Checklist has been refreshed.', 'success');
      }, 3000);

      return response;
    } catch (error) {
      console.error('Error resyncing checklist:', error);
      showNotification('Failed to resync checklist. Please try again later.', 'error');
      throw error;
    }
  });

  // Handle text match
  const handleMatch = () => {
    if (inputText.trim()) {
      matchMutation.mutate();
    }
  };

  // Handle item selection
  const handleItemSelect = (itemId: string) => {
    setSelectedItems((prev) =>
      prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [...prev, itemId]
    );
  };

  // Handle propose reference
  const handleProposeReference = () => {
    if (selectedItems.length > 0 && inputUrl) {
      proposeReferenceMutation.mutate();
    }
  };

  // Handle create PR
  const handleCreatePr = () => {
    createPrMutation.mutate();
  };

  // Handle delete pending change
  const handleDeletePendingChange = (changeId: number) => {
    deletePendingChangeMutation.mutate(changeId);
  };

  // Handle resync checklist
  const handleResync = () => {
    resyncMutation.mutate();
  };

  // Loading state
  const isLoading = isLoadingChecklist || isLoadingPendingChanges;

  // Main content based on active tab
  const renderContent = () => {
    if (activeTab === 'matcher') {
      return (
        <Grid container spacing={3} sx={{ height: 'calc(100vh - 150px)' }}>
          {/* Input Panel - Left Side */}
          <Grid item xs={12} md={6} sx={{ height: '100%' }}>
            <Paper sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
              <TextInputPanel
                inputText={inputText}
                setInputText={setInputText}
                inputUrl={inputUrl}
                setInputUrl={setInputUrl}
                onMatch={handleMatch}
                isLoading={matchMutation.isLoading}
              />
            </Paper>
          </Grid>

          {/* Match Results - Right Side */}
          <Grid item xs={12} md={6} sx={{ height: '100%' }}>
            <Paper sx={{ p: 3, height: '100%', overflow: 'auto' }}>
              {matchResults && (
                <MatchResults
                  results={matchResults}
                  selectedItems={selectedItems}
                  onItemSelect={handleItemSelect}
                  onProposeReference={handleProposeReference}
                  canProposeReference={selectedItems.length > 0 && !!inputUrl}
                  isProposing={proposeReferenceMutation.isLoading}
                />
              )}
              {!matchResults && (
                <Box sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: 'text.secondary'
                }}>
                  <Typography variant="h6">No Results Yet</Typography>
                  <Typography variant="body1">
                    Enter text in the input panel and click "Match with Checklist" to see results here.
                  </Typography>
                </Box>
              )}
            </Paper>
          </Grid>
        </Grid>
      );
    } else {
      return (
        <Paper sx={{ p: 3, height: 'calc(100vh - 150px)' }}>
          <PendingChanges
            pendingChanges={pendingChanges || []}
            checklist={checklist || []}
            onCreatePr={handleCreatePr}
            isCreatingPr={createPrMutation.isLoading}
            prResult={prResult}
            onDeleteChange={handleDeletePendingChange}
            isDeletingChange={deletePendingChangeMutation.isLoading}
          />
        </Paper>
      );
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        minHeight: '100vh' 
      }}>
        <AppBar position="static">
          <Toolbar>
            {/* Logo and Title */}
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <svg 
                width="38" 
                height="38" 
                viewBox="0 0 38 38" 
                fill="none" 
                xmlns="http://www.w3.org/2000/svg"
                style={{ marginRight: '12px' }}
              >
                <g filter="url(#filter0_dd_4_7222)">
                  <path d="M10.125 23.387L18.627 27.638C18.9812 27.8151 19.398 27.8151 19.7521 27.638L28.2542 23.387C28.8755 23.0763 29.1274 22.3207 28.8167 21.6993L20.3147 4.69534C19.8512 3.76822 18.5281 3.76822 18.0645 4.69534L9.56252 21.6994C9.25183 22.3207 9.50367 23.0763 10.125 23.387ZM17.5779 16.8216C17.5779 15.9315 18.2995 15.2099 19.1896 15.2099C20.0798 15.2099 20.8013 15.9315 20.8013 16.8216C20.8013 17.4375 20.4558 17.9725 19.9481 18.2438L20.8013 21.6568H17.5779L18.4312 18.2438C17.9235 17.9725 17.5779 17.4375 17.5779 16.8216Z" fill="#8058FF"/>
                  <path d="M27.5589 25.1511L19.7522 29.0545C19.3981 29.2315 18.9813 29.2315 18.6271 29.0545L10.8204 25.1511C9.98406 24.733 9 25.3411 9 26.2762C9 26.7527 9.2692 27.1883 9.69534 27.4013L18.6271 31.8672C18.9812 32.0443 19.3981 32.0443 19.7522 31.8672L28.684 27.4013C29.1101 27.1883 29.3793 26.7527 29.3793 26.2763C29.3793 25.3412 28.3952 24.733 27.5589 25.1511Z" fill="#4E38BA"/>
                </g>
                <defs>
                  <filter id="filter0_dd_4_7222" x="0" y="0" width="38.3793" height="41.0001" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
                    <feFlood flood-opacity="0" result="BackgroundImageFix"/>
                    <feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
                    <feOffset dy="1"/>
                    <feGaussianBlur stdDeviation="1"/>
                    <feColorMatrix type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.06 0"/>
                    <feBlend mode="normal" in2="BackgroundImageFix" result="effect1_dropShadow_4_7222"/>
                    <feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
                    <feOffset dy="4"/>
                    <feGaussianBlur stdDeviation="4.5"/>
                    <feColorMatrix type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.04 0"/>
                    <feBlend mode="normal" in2="effect1_dropShadow_4_7222" result="effect2_dropShadow_4_7222"/>
                    <feBlend mode="normal" in="SourceGraphic" in2="effect2_dropShadow_4_7222" result="shape"/>
                  </filter>
                </defs>
              </svg>
              <Typography variant="h6" component="div">
                Solodit Checklist Matcher
              </Typography>
            </Box>
            
            <Box sx={{ flexGrow: 1 }} />
            
            <Button
              color="inherit"
              onClick={() => setActiveTab('matcher')}
              sx={{
                borderBottom: activeTab === 'matcher' ? '2px solid white' : 'none',
                borderRadius: 0,
                mx: 1
              }}
            >
              Matcher
            </Button>
            <Button
              color="inherit"
              onClick={() => setActiveTab('pending')}
              sx={{
                borderBottom: activeTab === 'pending' ? '2px solid white' : 'none',
                borderRadius: 0,
                mx: 1
              }}
            >
              Pending Changes
              {pendingChanges && pendingChanges.length > 0 && (
                <Box
                  sx={{
                    ml: 1,
                    bgcolor: 'error.main',
                    color: 'error.contrastText',
                    borderRadius: '50%',
                    width: 20,
                    height: 20,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.75rem',
                  }}
                >
                  {pendingChanges.length}
                </Box>
              )}
            </Button>
            <Tooltip title="Refresh checklist from GitHub">
              <IconButton
                color="inherit"
                onClick={handleResync}
                disabled={resyncMutation.isLoading}
              >
                {resyncMutation.isLoading ? (
                  <CircularProgress size={24} color="inherit" />
                ) : (
                  <RefreshIcon />
                )}
              </IconButton>
            </Tooltip>
            
            {/* Theme toggle */}
            <Tooltip title={`Switch to ${mode === 'light' ? 'dark' : 'light'} mode`}>
              <IconButton color="inherit" onClick={toggleTheme}>
                {mode === 'light' ? <Brightness4Icon /> : <Brightness7Icon />}
              </IconButton>
            </Tooltip>
          </Toolbar>
        </AppBar>

        <Container maxWidth="xl" sx={{ mt: 4, mb: 4, flexGrow: 1 }}>
          {isLoading ? (
            <Backdrop open={true} sx={{ color: '#fff', zIndex: (theme) => theme.zIndex.drawer + 1 }}>
              <CircularProgress color="inherit" />
            </Backdrop>
          ) : isChecklistError || isPendingChangesError ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              Failed to load data. Please refresh the page or try again later.
            </Alert>
          ) : (
            renderContent()
          )}
        </Container>

        {/* Footer */}
        <Box
          component="footer"
          sx={{
            py: 2,
            px: 2,
            mt: 'auto',
            backgroundColor: (theme) =>
              theme.palette.mode === 'light'
                ? theme.palette.grey[200]
                : theme.palette.grey[800],
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '40px',
          }}
        >
          <Typography variant="body2" color="text.secondary" align="center" sx={{ display: 'flex', alignItems: 'center' }}>
            Built with <FavoriteIcon sx={{ color: 'red', fontSize: '1rem', verticalAlign: 'middle', mx: 0.5 }} /> for Cyfrin
          </Typography>
        </Box>

        {/* Global loading backdrop for long operations */}
        <Backdrop
          sx={{ color: '#fff', zIndex: (theme) => theme.zIndex.drawer + 1 }}
          open={resyncMutation.isLoading || createPrMutation.isLoading}
        >
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <CircularProgress color="inherit" />
            <Typography sx={{ mt: 2 }}>
              {resyncMutation.isLoading ? 'Resyncing checklist...' : 'Creating GitHub PR...'}
            </Typography>
          </Box>
        </Backdrop>

        {/* Notifications */}
        <Snackbar
          open={notification.open}
          autoHideDuration={6000}
          onClose={handleCloseNotification}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert onClose={handleCloseNotification} severity={notification.severity}>
            {notification.message}
          </Alert>
        </Snackbar>
      </Box>
    </ThemeProvider>
  );
}

// Wrap with QueryClientProvider
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App;