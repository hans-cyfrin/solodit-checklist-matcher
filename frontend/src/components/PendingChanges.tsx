import React, { useState } from 'react';
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  Button,
  Divider,
  CircularProgress,
  Alert,
  Link,
  Paper,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import InfoIcon from '@mui/icons-material/Info';
import { ChecklistItem, PendingChange } from '../App';

interface PendingChangesProps {
  pendingChanges: PendingChange[];
  checklist: ChecklistItem[];
  onCreatePr: () => void;
  isCreatingPr: boolean;
  prResult?: {
    pr_number: number;
    pr_url: string;
    num_changes: number;
  };
  onDeleteChange?: (changeId: number) => void;
  isDeletingChange?: boolean;
}

const PendingChanges: React.FC<PendingChangesProps> = ({
  pendingChanges,
  checklist,
  onCreatePr,
  isCreatingPr,
  prResult,
  onDeleteChange,
  isDeletingChange = false,
}) => {
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [changeToDelete, setChangeToDelete] = useState<number | null>(null);

  // Get checklist item by ID
  const getChecklistItem = (id: string) => {
    return checklist.find((item) => item.id === id);
  };

  // Filter pending changes based on search term
  const filteredChanges = pendingChanges.filter(change => {
    if (!searchTerm) return true;
    
    const searchLower = searchTerm.toLowerCase();
    const item = getChecklistItem(change.checklist_item_id);
    
    return (
      change.checklist_item_id.toLowerCase().includes(searchLower) ||
      change.source_url.toLowerCase().includes(searchLower) ||
      (item && item.category.toLowerCase().includes(searchLower)) ||
      (item && item.question.toLowerCase().includes(searchLower))
    );
  });

  // Group changes by category
  const changesByCategory: Record<string, PendingChange[]> = {};
  filteredChanges.forEach(change => {
    const item = getChecklistItem(change.checklist_item_id);
    const category = item ? item.category : 'Uncategorized';
    
    if (!changesByCategory[category]) {
      changesByCategory[category] = [];
    }
    
    changesByCategory[category].push(change);
  });

  // Handle PR confirmation
  const handleConfirmPR = () => {
    setConfirmDialogOpen(false);
    onCreatePr();
  };
  
  // Handle delete confirmation
  const handleConfirmDelete = () => {
    if (changeToDelete !== null && onDeleteChange) {
      onDeleteChange(changeToDelete);
      setDeleteDialogOpen(false);
      setChangeToDelete(null);
    }
  };
  
  // Open delete dialog
  const handleDeleteClick = (changeId: number) => {
    setChangeToDelete(changeId);
    setDeleteDialogOpen(true);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Pending Reference Changes
          <Tooltip title="These changes will be included in the next GitHub PR">
            <IconButton size="small" sx={{ ml: 1 }}>
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Typography>
        
        {pendingChanges.length > 0 && (
          <Button
            variant="contained"
            color="primary"
            onClick={() => setConfirmDialogOpen(true)}
            disabled={isCreatingPr}
            startIcon={isCreatingPr ? <CircularProgress size={20} color="inherit" /> : null}
          >
            {isCreatingPr ? 'Creating PR...' : 'Create GitHub PR'}
          </Button>
        )}
      </Box>

      {prResult && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Successfully created PR #{prResult.pr_number} with {prResult.num_changes} changes.{' '}
          <Link href={prResult.pr_url} target="_blank" rel="noopener noreferrer">
            View PR on GitHub
          </Link>
        </Alert>
      )}

      {pendingChanges.length === 0 ? (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            No pending changes. Match some text and propose references to see them here.
          </Typography>
        </Paper>
      ) : (
        <>
          <TextField
            fullWidth
            label="Search pending changes"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            margin="normal"
            size="small"
            sx={{ mb: 2 }}
          />
          
          {filteredChanges.length === 0 ? (
            <Typography variant="body1" color="text.secondary" sx={{ textAlign: 'center', mt: 2 }}>
              No changes match your search criteria.
            </Typography>
          ) : (
            Object.entries(changesByCategory).map(([category, changes]) => (
              <Paper key={category} sx={{ mb: 3, overflow: 'hidden' }}>
                <Box sx={{ bgcolor: 'primary.main', color: 'primary.contrastText', px: 2, py: 1 }}>
                  <Typography variant="subtitle1">{category}</Typography>
                </Box>
                <List>
                  {changes.map((change) => {
                    const item = getChecklistItem(change.checklist_item_id);
                    return (
                      <React.Fragment key={change.change_id}>
                        <ListItem 
                          alignItems="flex-start" 
                          sx={{ '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.04)' } }}
                          secondaryAction={
                            onDeleteChange && (
                              <Tooltip title="Delete this pending change">
                                <IconButton 
                                  edge="end" 
                                  aria-label="delete" 
                                  onClick={() => handleDeleteClick(change.change_id)}
                                  disabled={isDeletingChange}
                                >
                                  <DeleteIcon />
                                </IconButton>
                              </Tooltip>
                            )
                          }
                        >
                          <ListItemText
                            primary={
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Typography variant="subtitle1" fontWeight="bold">
                                  {change.checklist_item_id}
                                </Typography>
                                <Chip 
                                  label={change.status} 
                                  size="small" 
                                  color={change.status === 'pending' ? 'warning' : 'success'} 
                                />
                              </Box>
                            }
                            secondary={
                              <Box sx={{ mt: 1 }}>
                                {item && (
                                  <Typography variant="body2" gutterBottom>
                                    {item.question}
                                  </Typography>
                                )}
                                <Typography variant="body2" gutterBottom>
                                  <strong>Source URL:</strong>{' '}
                                  <Link href={change.source_url} target="_blank" rel="noopener noreferrer">
                                    {change.source_url}
                                  </Link>
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  Added on {new Date(change.created_at).toLocaleString()}
                                </Typography>
                              </Box>
                            }
                          />
                        </ListItem>
                        <Divider />
                      </React.Fragment>
                    );
                  })}
                </List>
              </Paper>
            ))
          )}
        </>
      )}

      {/* Confirmation Dialog for PR */}
      <Dialog open={confirmDialogOpen} onClose={() => setConfirmDialogOpen(false)}>
        <DialogTitle>Create GitHub Pull Request</DialogTitle>
        <DialogContent>
          <Typography>
            You are about to create a GitHub Pull Request with {pendingChanges.length} reference changes.
            This action will submit your changes to the Cyfrin/audit-checklist repository.
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Note: You need proper GitHub permissions for this action to succeed.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleConfirmPR} variant="contained" color="primary">
            Create PR
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Confirmation Dialog for Delete */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Pending Change</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this pending change? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleConfirmDelete} variant="contained" color="error">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PendingChanges;