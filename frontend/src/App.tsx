import React, { useState } from 'react';
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
  Tooltip
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { useQuery, useMutation, QueryClient, QueryClientProvider } from 'react-query';
import axios from 'axios';

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
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Solodit Checklist Matcher
          </Typography>
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
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
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