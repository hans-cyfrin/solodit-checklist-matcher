import React, { useState } from 'react';
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
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Grid,
  IconButton,
  Tooltip,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import FilterListIcon from '@mui/icons-material/FilterList';
import SortIcon from '@mui/icons-material/Sort';
import InfoIcon from '@mui/icons-material/Info';
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
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'score' | 'id'>('score');
  const [filterCategory, setFilterCategory] = useState<string>('');
  const [showFilters, setShowFilters] = useState(false);

  // Get unique categories
  const categories = Array.from(new Set(results.matches.map(item => item.category)));

  // Filter and sort matches
  const filteredMatches = React.useMemo(() => {
    if (!results || !results.matches) return [];
    
    let filtered = [...results.matches];
    
    // Apply category filter
    if (filterCategory && filterCategory !== 'All') {
      filtered = filtered.filter(item => item.category === filterCategory);
    }
    
    // Apply search filter
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      filtered = filtered.filter(
        item => 
          item.question.toLowerCase().includes(searchLower) ||
          item.description.toLowerCase().includes(searchLower) ||
          item.category.toLowerCase().includes(searchLower)
      );
    }
    
    // Sort results
    filtered.sort((a, b) => {
      if (sortBy === 'score') {
        // Sort by score (descending)
        return ((b.score || 0) - (a.score || 0));
      } else {
        // Sort by ID (ascending)
        return a.id.localeCompare(b.id);
      }
    });
    
    return filtered;
  }, [results, searchTerm, filterCategory, sortBy]);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Matching Checklist Items
          <Tooltip title="These items are semantically matched to your input text">
            <IconButton size="small" sx={{ ml: 1 }}>
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Typography>
        
        <Box>
          <Tooltip title="Show/Hide Filters">
            <IconButton onClick={() => setShowFilters(!showFilters)}>
              <FilterListIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {showFilters && (
        <Box sx={{ mb: 2, p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Search"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                size="small"
                placeholder="Search by ID, question, or description"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Sort By</InputLabel>
                <Select
                  value={sortBy}
                  label="Sort By"
                  onChange={(e) => setSortBy(e.target.value as 'score' | 'id')}
                >
                  <MenuItem value="score">Match Score</MenuItem>
                  <MenuItem value="id">ID</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Filter Category</InputLabel>
                <Select
                  value={filterCategory}
                  label="Filter Category"
                  onChange={(e) => setFilterCategory(e.target.value)}
                >
                  <MenuItem value="">All Categories</MenuItem>
                  {categories.map((category) => (
                    <MenuItem key={category} value={category}>
                      {category}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </Box>
      )}

      {results.matches.length === 0 ? (
        <Typography variant="body1" color="text.secondary">
          No matching checklist items found. Try a different description.
        </Typography>
      ) : filteredMatches.length === 0 ? (
        <Typography variant="body1" color="text.secondary">
          No items match your current filters. Try adjusting your search criteria.
        </Typography>
      ) : (
        <>
          <List>
            {filteredMatches.map((item) => (
              <React.Fragment key={item.id}>
                <ListItem alignItems="flex-start" sx={{ 
                  bgcolor: selectedItems.includes(item.id) ? 'rgba(25, 118, 210, 0.08)' : 'transparent',
                  transition: 'background-color 0.3s',
                  '&:hover': {
                    bgcolor: selectedItems.includes(item.id) ? 'rgba(25, 118, 210, 0.12)' : 'rgba(0, 0, 0, 0.04)',
                  }
                }}>
                  <Checkbox
                    edge="start"
                    checked={selectedItems.includes(item.id)}
                    onChange={() => onItemSelect(item.id)}
                  />
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                        <Typography variant="subtitle1" fontWeight="bold">{item.id}</Typography>
                        <Chip
                          label={`${Math.round(item.score! * 100)}% match`}
                          size="small"
                          color={item.score! > 0.7 ? 'success' : item.score! > 0.5 ? 'primary' : 'default'}
                          sx={{ fontWeight: 'bold' }}
                        />
                        <Chip label={item.category} size="small" variant="outlined" />
                      </Box>
                    }
                    secondary={
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="subtitle2" gutterBottom fontWeight="medium">
                          {item.question}
                        </Typography>

                        <Accordion>
                          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                            <Typography>Details</Typography>
                          </AccordionSummary>
                          <AccordionDetails>
                            <Typography variant="subtitle2" gutterBottom fontWeight="medium">
                              Description:
                            </Typography>
                            <Box sx={{ bgcolor: 'background.paper', p: 1, borderRadius: 1, mb: 2 }}>
                              <ReactMarkdown>{item.description}</ReactMarkdown>
                            </Box>

                            <Typography variant="subtitle2" gutterBottom fontWeight="medium">
                              Remediation:
                            </Typography>
                            <Box sx={{ bgcolor: 'background.paper', p: 1, borderRadius: 1, mb: 2 }}>
                              <ReactMarkdown>{item.remediation}</ReactMarkdown>
                            </Box>

                            {item.references.length > 0 && (
                              <>
                                <Typography variant="subtitle2" gutterBottom fontWeight="medium">
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
              {filteredMatches.length !== results.matches.length && 
                ` (showing ${filteredMatches.length} of ${results.matches.length})`}
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