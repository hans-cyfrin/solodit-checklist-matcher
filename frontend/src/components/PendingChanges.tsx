import React from 'react';
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
} from '@mui/material';
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
}

const PendingChanges: React.FC<PendingChangesProps> = ({
  pendingChanges,
  checklist,
  onCreatePr,
  isCreatingPr,
  prResult,
}) => {
  // Get checklist item by ID
  const getChecklistItem = (id: string) => {
    return checklist.find((item) => item.id === id);
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Pending Reference Changes
      </Typography>

      {prResult && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Successfully created PR #{prResult.pr_number} with {prResult.num_changes} changes.{' '}
          <Link href={prResult.pr_url} target="_blank" rel="noopener noreferrer">
            View PR on GitHub
          </Link>
        </Alert>
      )}

      {pendingChanges.length === 0 ? (
        <Typography variant="body1" color="text.secondary">
          No pending changes. Match some text and propose references to see them here.
        </Typography>
      ) : (
        <>
          <List>
            {pendingChanges.map((change) => {
              const item = getChecklistItem(change.checklist_item_id);
              return (
                <React.Fragment key={change.change_id}>
                  <ListItem alignItems="flex-start">
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="subtitle1">
                            {change.checklist_item_id}
                          </Typography>
                          {item && (
                            <Typography variant="body2" color="text.secondary">
                              {item.category}
                            </Typography>
                          )}
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

          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              variant="contained"
              color="primary"
              onClick={onCreatePr}
              disabled={isCreatingPr || pendingChanges.length === 0}
              startIcon={isCreatingPr ? <CircularProgress size={20} color="inherit" /> : null}
            >
              {isCreatingPr ? 'Creating PR...' : 'Create GitHub PR'}
            </Button>
          </Box>
        </>
      )}
    </Box>
  );
};

export default PendingChanges;