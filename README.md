# Solodit Checklist Matcher

*Enhanced Tool for Security Audit Collaboration*

## Overview

Solodit Checklist Matcher is a tool designed to help security auditors match findings from audit reports to standardized checklist items. It enables collaborative improvement of the [Cyfrin Audit Checklist](https://github.com/Cyfrin/audit-checklist) by allowing users to propose new references for checklist items.

## Features

- **Semantic Matching**: Uses NLP embeddings to match security issue descriptions to relevant checklist items
- **Reference Contribution**: Allows users to propose new reference URLs for checklist items
- **GitHub PR Automation**: Automatically creates pull requests to update the official checklist
- **Checklist Synchronization**: Keeps the local database in sync with the latest GitHub checklist

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with pgvector extension for vector embeddings
- **NLP**: sentence-transformers for semantic matching
- **GitHub Integration**: PyGithub for PR automation

### Frontend
- **Framework**: React with TypeScript
- **UI Components**: Material-UI
- **State Management**: React Query

## Getting Started

### Prerequisites
- Docker and Docker Compose
- GitHub token (for PR creation)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/solodit-checklist-matcher.git
   cd solodit-checklist-matcher
   ```

2. Create a `.env` file in the `backend` directory (copy from `.env.example`):
   ```
   cp backend/.env.example backend/.env
   ```

3. Edit the `.env` file to add your GitHub token:
   ```
   GITHUB_TOKEN=your_github_token
   ```

4. Start the application using Docker Compose:
   ```
   docker-compose up
   ```

5. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Usage

### Matching Text to Checklist Items

1. Enter a security issue description in the text area
2. Optionally provide a URL to the source
3. Click "Match with Checklist"
4. Review the matching results

### Proposing References

1. Select one or more matching checklist items
2. Ensure you've provided a source URL
3. Click "Propose Reference Update"
4. The proposed changes will be stored as pending changes

### Creating a GitHub PR

1. Navigate to the "Pending Changes" tab
2. Review the pending changes
3. Click "Create GitHub PR"
4. A PR will be automatically created in the Cyfrin/audit-checklist repository

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

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Cyfrin](https://github.com/Cyfrin) for the audit checklist
- [pgvector](https://github.com/pgvector/pgvector) for vector similarity search in PostgreSQL
- [sentence-transformers](https://github.com/UKPLab/sentence-transformers) for text embeddings