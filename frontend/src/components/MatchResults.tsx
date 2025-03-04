import React, { useState } from 'react';
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  Checkbox,
  Button,
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
  Link,
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
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h6" gutterBottom>
        Match Results
      </Typography>

      {/* Extracted Content Section */}
      <Box sx={{ 
        mb: 2, 
        p: 2, 
        bgcolor: results.preprocessing_applied ? '#e3f2fd' : '#f5f5f5', 
        borderRadius: 1,
        border: results.preprocessing_applied ? '1px solid #90caf9' : 'none'
      }}>
        <Typography variant="subtitle2" gutterBottom color={results.preprocessing_applied ? 'primary' : 'textSecondary'}>
          {results.preprocessing_applied 
            ? 'AI-Processed Content:' 
            : 'Original Content:'}
        </Typography>
        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
          {results.preprocessed_text || results.input_text}
        </Typography>
        {results.preprocessing_applied && (
          <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mt: 1 }}>
            The content above has been processed by AI to extract the most relevant technical details.
          </Typography>
        )}
      </Box>

      <Box sx={{ mb: 2, display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
        <TextField
          label="Search"
          variant="outlined"
          size="small"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          sx={{ flexGrow: 1, minWidth: '200px' }}
        />

        <FormControl size="small" sx={{ minWidth: '150px' }}>
          <InputLabel id="category-filter-label">Category</InputLabel>
          <Select
            labelId="category-filter-label"
            value={filterCategory}
            label="Category"
            onChange={(e) => setFilterCategory(e.target.value)}
          >
            <MenuItem value="All">All Categories</MenuItem>
            {Array.from(new Set(results.matches.map(item => item.category))).map(category => (
              <MenuItem key={category} value={category}>{category}</MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: '120px' }}>
          <InputLabel id="sort-by-label">Sort By</InputLabel>
          <Select
            labelId="sort-by-label"
            value={sortBy}
            label="Sort By"
            onChange={(e) => setSortBy(e.target.value as 'score' | 'id')}
          >
            <MenuItem value="score">Relevance</MenuItem>
            <MenuItem value="id">ID</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        {filteredMatches.length === 0 ? (
          <Typography variant="body1" sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
            No matches found. Try adjusting your search or filters.
          </Typography>
        ) : (
          filteredMatches.map((item) => (
            <Accordion key={item.id} sx={{ mb: 1 }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                  <Checkbox
                    checked={selectedItems.includes(item.id)}
                    onChange={() => onItemSelect(item.id)}
                    onClick={(e) => e.stopPropagation()}
                  />
                  <Box sx={{ ml: 1, flexGrow: 1 }}>
                    <Typography variant="subtitle1">
                      {item.question}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        label={item.category}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                      {item.score !== undefined && (
                        <Chip
                          label={`Score: ${(item.score * 100).toFixed(0)}%`}
                          size="small"
                          color={item.score > 0.7 ? 'success' : item.score > 0.5 ? 'warning' : 'default'}
                          variant="outlined"
                        />
                      )}
                    </Box>
                  </Box>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Typography variant="body2" gutterBottom>
                  <ReactMarkdown>{item.description}</ReactMarkdown>
                </Typography>
                {item.remediation && (
                  <>
                    <Typography variant="subtitle2" gutterBottom sx={{ mt: 1 }}>
                      Remediation:
                    </Typography>
                    <Typography variant="body2" gutterBottom>
                      <ReactMarkdown>{item.remediation}</ReactMarkdown>
                    </Typography>
                  </>
                )}
                {item.references && item.references.length > 0 && (
                  <>
                    <Typography variant="subtitle2" gutterBottom sx={{ mt: 1 }}>
                      References:
                    </Typography>
                    <List dense>
                      {item.references.map((ref, index) => (
                        <ListItem key={index} sx={{ py: 0 }}>
                          <ListItemText
                            primary={
                              ref.startsWith('http') ? (
                                <Link href={ref} target="_blank" rel="noopener noreferrer">
                                  {ref}
                                </Link>
                              ) : ref
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  </>
                )}
              </AccordionDetails>
            </Accordion>
          ))
        )}
      </Box>

      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          color="primary"
          onClick={onProposeReference}
          disabled={!canProposeReference || isProposing}
          startIcon={isProposing ? <CircularProgress size={20} color="inherit" /> : null}
        >
          {isProposing ? 'Proposing...' : 'Propose Reference'}
        </Button>
      </Box>
    </Box>
  );
};

export default MatchResults;