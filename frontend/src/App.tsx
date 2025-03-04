import React, { useState } from 'react';
import { Container, Box, Typography, Paper, AppBar, Toolbar, Button } from '@mui/material';
import { useQuery, useMutation } from 'react-query';
import axios from 'axios';

import TextInputPanel from './components/TextInputPanel';
import MatchResults from './components/MatchResults';
import PendingChanges from './components/PendingChanges';

// API base URL
const API_BASE_URL = 'http://localhost:8000';

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

function App() {
  // State
  const [inputText, setInputText] = useState('');
  const [inputUrl, setInputUrl] = useState('');
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [matchResults, setMatchResults] = useState<MatchResult | null>(null);
  const [activeTab, setActiveTab] = useState<'matcher' | 'pending'>('matcher');

  // Fetch checklist
  const { data: checklist } = useQuery<ChecklistItem[]>('checklist', async () => {
    const response = await axios.get(`${API_BASE_URL}/checklist`);
    return response.data;
  });

  // Fetch pending changes
  const { data: pendingChanges, refetch: refetchPendingChanges } = useQuery<PendingChange[]>(
    'pendingChanges',
    async () => {
      const response = await axios.get(`${API_BASE_URL}/pending-changes`);
      return response.data;
    }
  );

  // Match text mutation
  const matchMutation = useMutation(async () => {
    const response = await axios.post(`${API_BASE_URL}/match`, {
      text: inputText,
      url: inputUrl || undefined,
    });
    setMatchResults(response.data);
    return response.data;
  });

  // Propose reference mutation
  const proposeReferenceMutation = useMutation(
    async () => {
      const changes = selectedItems.map((itemId) => ({
        checklist_item_id: itemId,
        source_url: inputUrl,
      }));
      const response = await axios.post(`${API_BASE_URL}/propose-reference`, changes);
      return response.data;
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
    const response = await axios.post(`${API_BASE_URL}/create-pr`);
    return response.data;
  });

  // Resync checklist mutation
  const resyncMutation = useMutation(async () => {
    const response = await axios.post(`${API_BASE_URL}/resync`);
    return response.data;
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

  // Handle resync checklist
  const handleResync = () => {
    resyncMutation.mutate();
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Solodit Checklist Matcher
          </Typography>
          <Button color="inherit" onClick={() => setActiveTab('matcher')}>
            Matcher
          </Button>
          <Button color="inherit" onClick={() => setActiveTab('pending')}>
            Pending Changes
          </Button>
          <Button color="inherit" onClick={handleResync}>
            Resync Checklist
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4 }}>
        {activeTab === 'matcher' ? (
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
            />
          </Paper>
        )}
      </Container>
    </Box>
  );
}

export default App;