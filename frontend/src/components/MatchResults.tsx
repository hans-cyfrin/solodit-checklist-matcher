import React from 'react';
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  Checkbox,
  Button,
  Divider,
  Chip,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ReactMarkdown from 'react-markdown';
import { MatchResult } from '../App';

interface MatchResultsProps {
  results: MatchResult;
  selectedItems: string[];
  onItemSelect: (itemId: string) => void;
  onProposeReference: () => void;
  canProposeReference: boolean;
  isProposing: boolean;
}

const MatchResults: React.FC<MatchResultsProps> = ({
  results,
  selectedItems,
  onItemSelect,
  onProposeReference,
  canProposeReference,
  isProposing,
}) => {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Matching Checklist Items
      </Typography>

      {results.matches.length === 0 ? (
        <Typography variant="body1" color="text.secondary">
          No matching checklist items found. Try a different description.
        </Typography>
      ) : (
        <>
          <List>
            {results.matches.map((item) => (
              <React.Fragment key={item.id}>
                <ListItem alignItems="flex-start">
                  <Checkbox
                    edge="start"
                    checked={selectedItems.includes(item.id)}
                    onChange={() => onItemSelect(item.id)}
                  />
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="subtitle1">{item.id}</Typography>
                        <Chip
                          label={`${Math.round(item.score! * 100)}% match`}
                          size="small"
                          color={item.score! > 0.7 ? 'success' : item.score! > 0.5 ? 'primary' : 'default'}
                        />
                        <Chip label={item.category} size="small" variant="outlined" />
                      </Box>
                    }
                    secondary={
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          {item.question}
                        </Typography>

                        <Accordion>
                          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                            <Typography>Details</Typography>
                          </AccordionSummary>
                          <AccordionDetails>
                            <Typography variant="subtitle2" gutterBottom>
                              Description:
                            </Typography>
                            <ReactMarkdown>{item.description}</ReactMarkdown>

                            <Typography variant="subtitle2" gutterBottom>
                              Remediation:
                            </Typography>
                            <ReactMarkdown>{item.remediation}</ReactMarkdown>

                            {item.references.length > 0 && (
                              <>
                                <Typography variant="subtitle2" gutterBottom>
                                  References:
                                </Typography>
                                <List dense>
                                  {item.references.map((ref, index) => (
                                    <ListItem key={index}>
                                      <ListItemText>
                                        <a href={ref} target="_blank" rel="noopener noreferrer">
                                          {ref}
                                        </a>
                                      </ListItemText>
                                    </ListItem>
                                  ))}
                                </List>
                              </>
                            )}
                          </AccordionDetails>
                        </Accordion>
                      </Box>
                    }
                  />
                </ListItem>
                <Divider />
              </React.Fragment>
            ))}
          </List>

          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="body2">
              {selectedItems.length} item{selectedItems.length !== 1 ? 's' : ''} selected
            </Typography>

            <Button
              variant="contained"
              color="primary"
              onClick={onProposeReference}
              disabled={!canProposeReference || isProposing}
              startIcon={isProposing ? <CircularProgress size={20} color="inherit" /> : null}
            >
              {isProposing ? 'Proposing...' : 'Propose Reference Update'}
            </Button>
          </Box>
        </>
      )}
    </Box>
  );
};

export default MatchResults;