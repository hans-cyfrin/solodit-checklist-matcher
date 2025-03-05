# Solodit Checklist Matcher


## Overview

Solodit Checklist Matcher is a tool designed to help security auditors match findings from audit reports to standardized checklist items. It enables collaborative improvement of the [Cyfrin Audit Checklist](https://github.com/Cyfrin/audit-checklist) by allowing users to propose new references for checklist items.

## Features

- **Semantic Matching**: Uses NLP embeddings to match security issue descriptions to relevant checklist items
- **Reference Contribution**: Allows users to propose new reference URLs for checklist items
- **GitHub PR Automation**: Automatically creates pull requests to update the official checklist
- **Checklist Synchronization**: Keeps the local database in sync with the latest GitHub checklist
- **Efficient Caching**: Implements embedding caching for better performance
- **Responsive UI**: Modern interface with filtering, sorting, and search capabilities

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with pgvector extension for vector embeddings
- **NLP**: sentence-transformers for semantic matching
- **GitHub Integration**: PyGithub for PR automation

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

2. Create a `.env` file in the root directory (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file to add your tokens and configure the environment:
   ```
   # Database configuration
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_secure_password
   POSTGRES_DB=solodit_checklist
   DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}

   # GitHub configuration
   GITHUB_TOKEN=your_github_token
   GITHUB_REPO_OWNER=Cyfrin
   GITHUB_REPO_NAME=audit-checklist
   GITHUB_PR_BRANCH=solodit-matcher-updates

   # API configuration
   API_HOST=0.0.0.0
   API_PORT=8000
   CORS_ORIGINS=http://localhost:3000

   # OpenAI configuration
   OPENAI_API_KEY=your_openai_api_key
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
   # Create a database named 'solodit_checklist'
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