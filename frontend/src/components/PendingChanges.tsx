import React, { useState } from 'react';
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  Button,
  CircularProgress,
  Alert,
  Link,
  Paper,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
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
    if (!checklist || !Array.isArray(checklist)) return null;
    return checklist.find(item => item.id === id) || null;
  };

  // Filter pending changes based on search term
  const filteredChanges = pendingChanges.filter(change => {
    if (!searchTerm) return true;
    
    const searchLower = searchTerm.toLowerCase();
    const item = getChecklistItem(change.checklist_item_id);
    
    return (
      (item && (
        item.question.toLowerCase().includes(searchLower) ||
        item.description.toLowerCase().includes(searchLower) ||
        item.category.toLowerCase().includes(searchLower)
      )) ||
      change.source_url.toLowerCase().includes(searchLower)
    );
  });

  // Group changes by checklist item
  const changesByItem: Record<string, PendingChange[]> = {};
  
  if (filteredChanges && Array.isArray(filteredChanges)) {
    filteredChanges.forEach(change => {
      if (!change || !change.checklist_item_id) return;
      
      if (!changesByItem[change.checklist_item_id]) {
        changesByItem[change.checklist_item_id] = [];
      }
      
      changesByItem[change.checklist_item_id].push(change);
    });
  }

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
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Pending Changes</Typography>
        <Box>
          <Button
            variant="contained"
            color="primary"
            onClick={() => setConfirmDialogOpen(true)}
            disabled={!pendingChanges || pendingChanges.length === 0 || isCreatingPr}
            startIcon={isCreatingPr ? <CircularProgress size={20} color="inherit" /> : null}
          >
            {isCreatingPr ? 'Creating PR...' : 'Create PR'}
          </Button>
        </Box>
      </Box>

      {prResult && (
        <Alert severity="success" sx={{ mb: 2 }}>
          <Typography>
            PR #{prResult.pr_number} created successfully with {prResult.num_changes} changes.{' '}
            <Link href={prResult.pr_url} target="_blank" rel="noopener noreferrer">
              View on GitHub
            </Link>
          </Typography>
        </Alert>
      )}

      <Box sx={{ mb: 2 }}>
        <TextField
          label="Search"
          variant="outlined"
          size="small"
          fullWidth
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search by checklist item or URL..."
        />
      </Box>

      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        {pendingChanges && pendingChanges.length === 0 ? (
          <Typography variant="body1" sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
            No pending changes. Match some text and propose references to see them here.
          </Typography>
        ) : (
          <Box>
            {Object.entries(changesByItem).map(([checklistItemId, changes]) => {
              const item = getChecklistItem(checklistItemId);
              if (!item) return null;
              
              return (
                <Paper key={checklistItemId} sx={{ mb: 3, overflow: 'hidden' }}>
                  <Box sx={{ bgcolor: 'primary.main', color: 'primary.contrastText', px: 2, py: 1 }}>
                    <Typography variant="subtitle1">
                      {item.category} - {item.question}
                    </Typography>
                  </Box>
                  
                  <Box sx={{ p: 2 }}>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      {item.description}
                    </Typography>
                    
                    <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                      Proposed References:
                    </Typography>
                    
                    <List dense>
                      {changes.map((change) => (
                        <ListItem
                          key={change.change_id}
                          secondaryAction={
                            onDeleteChange && (
                              <Tooltip title="Delete this proposed reference">
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
                              <Link
                                href={change.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                sx={{ wordBreak: 'break-all' }}
                              >
                                {change.source_url}
                              </Link>
                            }
                            secondary={`Added: ${new Date(change.created_at).toLocaleString()}`}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                </Paper>
              );
            })}
          </Box>
        )}
      </Box>

      {/* Confirmation Dialog for PR Creation */}
      <Dialog open={confirmDialogOpen} onClose={() => setConfirmDialogOpen(false)}>
        <DialogTitle>Create Pull Request</DialogTitle>
        <DialogContent>
          <Typography>
            This will create a pull request to update the checklist with all pending changes.
            Are you sure you want to continue?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleConfirmPR} variant="contained" color="primary">
            Create PR
          </Button>
        </DialogActions>
      </Dialog>

      {/* Confirmation Dialog for Deletion */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Pending Change</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this pending change?
            This action cannot be undone.
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