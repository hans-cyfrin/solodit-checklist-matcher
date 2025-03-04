# Solodit Checklist Matcher

*Enhanced Tool for Security Audit Collaboration*

## Overview

Solodit Checklist Matcher is a tool designed to help security auditors match findings from audit reports to standardized checklist items. It enables collaborative improvement of the [Cyfrin Audit Checklist](https://github.com/Cyfrin/audit-checklist) by allowing users to propose new references for checklist items.

## Features

- **Semantic Matching**: Uses NLP embeddings to match security issue descriptions to relevant checklist items
- **Reference Contribution**: Allows users to propose new reference URLs for checklist items
- **GitHub PR Automation**: Automatically creates pull requests to update the official checklist
- **Checklist Synchronization**: Keeps the local database in sync with the latest GitHub checklist
- **Efficient Caching**: Implements embedding caching for better performance
- **Rate Limiting**: Protects API endpoints from abuse
- **Responsive UI**: Modern interface with filtering, sorting, and search capabilities

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with pgvector extension for vector embeddings
- **NLP**: sentence-transformers for semantic matching
- **GitHub Integration**: PyGithub for PR automation
- **Rate Limiting**: SlowAPI for API protection

### Frontend
- **Framework**: React with TypeScript
- **UI Components**: Material-UI
- **State Management**: React Query for data fetching and caching
- **Notifications**: Snackbar notifications for user feedback

## Getting Started

### Prerequisites
- Docker and Docker Compose (recommended)
- GitHub token (for PR creation)
- PostgreSQL with pgvector extension (if running without Docker)
- Node.js and npm (if running frontend without Docker)
- Python 3.8+ (if running backend without Docker)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/solodit-checklist-matcher.git
   cd solodit-checklist-matcher
   ```

2. Create a `.env` file in the `backend` directory (copy from `.env.example`):
   ```bash
   cp backend/.env.example backend/.env
   ```

3. Edit the `.env` file to add your GitHub token and configure database:
   ```
   # Database configuration
   DATABASE_URL=postgresql://postgres:postgres@db:5432/solodit
   
   # GitHub configuration
   GITHUB_TOKEN=your_github_token
   GITHUB_REPO_OWNER=Cyfrin
   GITHUB_REPO_NAME=audit-checklist
   GITHUB_PR_BRANCH=solodit-matcher-updates
   
   # API configuration
   API_HOST=0.0.0.0
   API_PORT=8000
   CORS_ORIGINS=http://localhost:3000
   ```

4. Start the application:

   **Using Docker Compose (recommended):**
   ```bash
   docker-compose up -d
   ```

   **Without Docker:**
   
   a. Set up PostgreSQL with pgvector:
   ```bash
   # Install pgvector extension in your PostgreSQL instance
   # Create a database named 'solodit'
   ```
   
   b. Start the backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   python -m uvicorn main:app --reload
   ```
   
   c. Start the frontend:
   ```bash
   cd frontend
   npm install
   npm start
   ```

5. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Usage

### Matching Text to Checklist Items

1. Enter a security issue description in the text area
2. Optionally provide a URL to the source (must be HTTPS for security)
3. Click "Match with Checklist"
4. Review the matching results
5. Use the filtering and sorting options to find relevant items

### Proposing References

1. Select one or more matching checklist items
2. Ensure you've provided a source URL
3. Click "Propose Reference Update"
4. The proposed changes will be stored as pending changes

### Managing Pending Changes

1. Navigate to the "Pending Changes" tab
2. Review the pending changes grouped by category
3. Use the search box to filter pending changes
4. Delete any unwanted changes using the delete button
5. Click "Create GitHub PR" when ready to submit changes

### Creating a GitHub PR

1. From the "Pending Changes" tab, click "Create GitHub PR"
2. Confirm the action in the dialog
3. A PR will be automatically created in the Cyfrin/audit-checklist repository
4. View the PR link in the success notification

### Resyncing the Checklist

1. Click the refresh icon in the top navigation bar
2. The application will fetch the latest checklist from GitHub
3. New items will be added to the database and embeddings will be generated

## API Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/checklist` | GET | Get all checklist items | - |
| `/match` | POST | Match text to checklist items | 20/minute |
| `/propose-reference` | POST | Propose new references | 10/minute |
| `/pending-changes` | GET | Get all pending changes | - |
| `/pending-changes/{id}` | DELETE | Delete a pending change | - |
| `/create-pr` | POST | Create a GitHub PR | 5/hour |
| `/resync` | POST | Resync checklist from GitHub | 2/hour |
| `/health` | GET | Check application health | - |

## Development

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm start
```

### Running Tests

```bash
cd backend
python run_tests.py
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   - Check if PostgreSQL is running
   - Verify database credentials in `.env`
   - Ensure pgvector extension is installed

2. **GitHub API Errors**:
   - Verify your GitHub token has sufficient permissions
   - Check if you've hit GitHub API rate limits

3. **Embedding Model Issues**:
   - Ensure you have sufficient RAM (at least 4GB)
   - Check for compatible versions of dependencies

### Health Check

The application provides a health check endpoint at `/health` that reports the status of:
- Database connection
- GitHub API access
- Embedding model initialization

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Cyfrin](https://github.com/Cyfrin) for the audit checklist
- [pgvector](https://github.com/pgvector/pgvector) for vector similarity search in PostgreSQL
- [sentence-transformers](https://github.com/UKPLab/sentence-transformers) for text embeddings
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework
- [React](https://reactjs.org/) and [Material-UI](https://mui.com/) for the frontend