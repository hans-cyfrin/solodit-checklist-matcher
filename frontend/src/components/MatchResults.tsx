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
  useTheme,
  alpha,
  Tabs,
  Tab,
  Paper,
  Divider
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ReactMarkdown from 'react-markdown';
import { MatchResult, GeneratedCheckItem } from '../App';

interface MatchResultsProps {
  results: MatchResult;
  selectedItems: string[];
  onItemSelect: (itemId: string) => void;
  onProposeReference: () => void;
  canProposeReference: boolean;
  isProposing: boolean;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`match-tabpanel-${index}`}
      aria-labelledby={`match-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const MatchResults: React.FC<MatchResultsProps> = ({
  results,
  selectedItems,
  onItemSelect,
  onProposeReference,
  canProposeReference,
  isProposing,
}) => {
  const theme = useTheme();
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'score' | 'id'>('score');
  const [filterCategory, setFilterCategory] = useState<string>('');
  const [tabValue, setTabValue] = useState(0);

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

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const renderCheckItem = (item: GeneratedCheckItem, label: string) => (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
        {label}
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Chip 
          label={`Confidence: ${(item.confidence * 100).toFixed(0)}%`}
          color={item.confidence > 0.7 ? "success" : "warning"}
          size="small" 
        />
      </Box>
      <Typography variant="subtitle1" gutterBottom>
        {item.question}
      </Typography>
      <Typography variant="body2" gutterBottom>
        {item.description}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {item.remediation}
      </Typography>
    </Paper>
  );

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h6" gutterBottom>
        Match Results
      </Typography>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="match results tabs">
          <Tab label="Matches" />
          <Tab label="Generated Items" />
        </Tabs>
      </Box>

      <Box sx={{ flexGrow: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <TabPanel value={tabValue} index={0}>
          <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
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
                  <MenuItem value="">All Categories</MenuItem>
                  {categories.map(category => (
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

            <Box sx={{ flexGrow: 1, overflow: 'auto', mb: 2 }}>
              {filteredMatches.length === 0 ? (
                <Typography variant="body1" sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
                  No matches found. Try adjusting your search or filters.
                </Typography>
              ) : (
                filteredMatches.map((item) => (
                  <Accordion
                    key={item.id}
                    sx={{
                      mb: 1,
                      backgroundColor: theme.palette.mode === 'dark'
                        ? alpha(theme.palette.background.paper, 0.8)
                        : theme.palette.background.paper,
                      '&:hover': {
                        backgroundColor: theme.palette.mode === 'dark'
                          ? alpha(theme.palette.background.paper, 1)
                          : theme.palette.background.paper,
                      }
                    }}
                  >
                    <AccordionSummary
                      expandIcon={<ExpandMoreIcon />}
                      sx={{
                        borderLeft: item.score && item.score > 0.7
                          ? `4px solid ${theme.palette.success.main}`
                          : item.score && item.score > 0.5
                            ? `4px solid ${theme.palette.warning.main}`
                            : 'none'
                      }}
                    >
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
                            />
                            {item.score && (
                              <Chip
                                label={`Match: ${(item.score * 100).toFixed(0)}%`}
                                size="small"
                                color={item.score > 0.7 ? "success" : "warning"}
                              />
                            )}
                          </Box>
                        </Box>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Typography variant="body1" paragraph>
                        {item.description}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        <strong>Remediation:</strong> {item.remediation}
                      </Typography>
                      {item.references && item.references.length > 0 && (
                        <Box sx={{ mt: 2 }}>
                          <Typography variant="subtitle2" gutterBottom>
                            References:
                          </Typography>
                          <List dense>
                            {item.references.map((ref: string, index: number) => (
                              <ListItem key={index}>
                                <Link href={ref} target="_blank" rel="noopener noreferrer">
                                  {ref}
                                </Link>
                              </ListItem>
                            ))}
                          </List>
                        </Box>
                      )}
                    </AccordionDetails>
                  </Accordion>
                ))
              )}
            </Box>
          </Box>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ flexGrow: 1, overflow: 'auto', mb: 2 }}>
              {/* Generated Items Section */}
              <Typography variant="h6" gutterBottom>
                Generated Items
              </Typography>
              <Box sx={{ mb: 3 }}>
                {results.generated_items.map((item, index) => (
                  <Paper key={index} sx={{ p: 2, mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      {item.question}
                    </Typography>
                    <Typography variant="body2" gutterBottom>
                      {item.description}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {item.remediation}
                    </Typography>
                  </Paper>
                ))}
              </Box>

              {/* Final Item Section */}
              <Box sx={{ mt: 4 }}>
                <Typography variant="h6" gutterBottom>
                  Final Improved Item
                </Typography>
                <Paper sx={{ p: 2, bgcolor: theme.palette.mode === 'dark' ? alpha(theme.palette.primary.main, 0.1) : alpha(theme.palette.primary.main, 0.05) }}>
                  <Typography variant="subtitle1" gutterBottom>
                    {results.final_item.question}
                  </Typography>
                  <Typography variant="body2" gutterBottom>
                    {results.final_item.description}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {results.final_item.remediation}
                  </Typography>
                </Paper>
              </Box>
            </Box>
          </Box>
        </TabPanel>
      </Box>

      {canProposeReference && (
        <Box sx={{ pt: 2 }}>
          <Button
            variant="contained"
            color="primary"
            fullWidth
            onClick={onProposeReference}
            disabled={selectedItems.length === 0 || isProposing}
          >
            {isProposing ? (
              <>
                <CircularProgress size={24} color="inherit" sx={{ mr: 1 }} />
                Proposing...
              </>
            ) : (
              `Propose Reference (${selectedItems.length} selected)`
            )}
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default MatchResults;