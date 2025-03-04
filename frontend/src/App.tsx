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
  IconButton
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
}

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
      const response = await axios.get(`${API_BASE_URL}/checklist`);
      return response.data;
    } catch (error) {
      console.error('Error fetching checklist:', error);
      showNotification('Failed to load checklist items. Please try again later.', 'error');
      throw error;
    }
  });

  // Fetch pending changes
  const { 
    data: pendingChanges, 
    isLoading: isLoadingPendingChanges,
    isError: isPendingChangesError,
    refetch: refetchPendingChanges 
  } = useQuery<PendingChange[]>(
    'pendingChanges',
    async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/pending-changes`);
        return response.data;
      } catch (error) {
        console.error('Error fetching pending changes:', error);
        showNotification('Failed to load pending changes. Please try again later.', 'error');
        throw error;
      }
    }
  );

  // Match text mutation
  const matchMutation = useMutation(async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/match`, {
        text: inputText,
        url: inputUrl || undefined,
      });
      setMatchResults(response.data);
      
      if (response.data.matches.length === 0) {
        showNotification('No matching checklist items found. Try a different description.', 'info');
      } else {
        showNotification(`Found ${response.data.matches.length} matching checklist items.`, 'success');
      }
      
      return response.data;
    } catch (error) {
      console.error('Error matching text:', error);
      showNotification('Failed to match text. Please try again later.', 'error');
      throw error;
    }
  });

  // Propose reference mutation
  const proposeReferenceMutation = useMutation(
    async () => {
      try {
        const changes = selectedItems.map((itemId) => ({
          checklist_item_id: itemId,
          source_url: inputUrl,
        }));
        const response = await axios.post(`${API_BASE_URL}/propose-reference`, changes);
        showNotification(`Successfully proposed ${changes.length} reference updates.`, 'success');
        return response.data;
      } catch (error) {
        console.error('Error proposing reference:', error);
        showNotification('Failed to propose reference updates. Please try again later.', 'error');
        throw error;
      }
    },
    {
      onSuccess: () => {
        refetchPendingChanges();
        setSelectedItems([]);
        setActiveTab('pending');
      },
    }
  );

  // Create PR mutation
  const createPrMutation = useMutation(async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/create-pr`);
      
      if (response.data.pr_number) {
        showNotification(`Successfully created PR #${response.data.pr_number}.`, 'success');
      } else {
        showNotification('All changes were already applied. No new PR was created.', 'info');
      }
      
      return response.data;
    } catch (error) {
      console.error('Error creating PR:', error);
      showNotification('Failed to create PR. Please check your GitHub permissions.', 'error');
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
        const response = await axios.delete(`${API_BASE_URL}/pending-changes/${changeId}`);
        showNotification('Pending change deleted successfully.', 'success');
        return response.data;
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
      const response = await axios.post(`${API_BASE_URL}/resync`);
      showNotification('Checklist resync started. This may take a moment.', 'info');
      
      // Wait a bit and then refetch the checklist
      setTimeout(() => {
        refetchChecklist();
        showNotification('Checklist has been refreshed.', 'success');
      }, 3000);
      
      return response.data;
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
          <IconButton 
            color="inherit" 
            onClick={handleResync}
            disabled={resyncMutation.isLoading}
            sx={{ ml: 1 }}
          >
            {resyncMutation.isLoading ? (
              <CircularProgress size={24} color="inherit" />
            ) : (
              <RefreshIcon />
            )}
          </IconButton>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4 }}>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
            <CircularProgress />
          </Box>
        ) : isChecklistError || isPendingChangesError ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to load data from the server. Please check your connection and try again.
            <Button onClick={() => window.location.reload()} sx={{ ml: 2 }}>
              Reload Page
            </Button>
          </Alert>
        ) : (
          activeTab === 'matcher' ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Paper sx={{ p: 2 }}>
                <TextInputPanel
                  inputText={inputText}
                  setInputText={setInputText}
                  inputUrl={inputUrl}
                  setInputUrl={setInputUrl}
                  onMatch={handleMatch}
                  isLoading={matchMutation.isLoading}
                />
              </Paper>

              {matchResults && (
                <Paper sx={{ p: 2 }}>
                  <MatchResults
                    results={matchResults}
                    selectedItems={selectedItems}
                    onItemSelect={handleItemSelect}
                    onProposeReference={handleProposeReference}
                    canProposeReference={!!inputUrl && selectedItems.length > 0}
                    isProposing={proposeReferenceMutation.isLoading}
                  />
                </Paper>
              )}
            </Box>
          ) : (
            <Paper sx={{ p: 2 }}>
              <PendingChanges
                pendingChanges={pendingChanges || []}
                checklist={checklist || []}
                onCreatePr={handleCreatePr}
                isCreatingPr={createPrMutation.isLoading}
                prResult={createPrMutation.data}
                onDeleteChange={handleDeletePendingChange}
                isDeletingChange={deletePendingChangeMutation.isLoading}
              />
            </Paper>
          )
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