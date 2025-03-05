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

## Deployment

### AWS EC2 Free Tier Deployment

1. Launch an EC2 Instance:
   - Choose Amazon Linux 2023 AMI (free tier eligible)
   - Select t2.micro instance type
   - Configure security group to allow:
     - SSH (port 22)
     - HTTP (port 80)
     - HTTPS (port 443)
     - Custom TCP (ports 8000 for API, 3000 for frontend)

2. Install System Dependencies:
   ```bash
   # Update system
   sudo yum update -y

   # Install development tools
   sudo yum groupinstall "Development Tools" -y
   
   # Install Python 3.8+ and pip
   sudo yum install python3 python3-pip -y
   
   # Install Node.js and npm
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
   source ~/.bashrc
   nvm install 18
   nvm use 18

   # Install PostgreSQL 15 with pgvector
   sudo yum install -y postgresql15 postgresql15-server
   sudo postgresql-setup --initdb
   ```

3. Configure PostgreSQL:
   ```bash
   # Start PostgreSQL service
   sudo systemctl start postgresql
   sudo systemctl enable postgresql

   # Switch to postgres user
   sudo -i -u postgres

   # Create database and user
   createdb solodit_checklist
   psql -c "CREATE USER solodit WITH PASSWORD 'your_secure_password';"
   psql -c "GRANT ALL PRIVILEGES ON DATABASE solodit_checklist TO solodit;"

   # Install pgvector extension
   psql -d solodit_checklist -c 'CREATE EXTENSION vector;'

   # Exit postgres user
   exit
   ```

4. Clone and Setup Application:
   ```bash
   # Clone repository
   git clone https://github.com/yourusername/solodit-checklist-matcher.git
   cd solodit-checklist-matcher

   # Create and configure .env
   cp .env.example .env
   
   # Edit .env with your configuration:
   nano .env
   ```
   Update the `.env` file with:
   ```
   # Database configuration
   POSTGRES_USER=solodit
   POSTGRES_PASSWORD=your_secure_password
   POSTGRES_DB=solodit_checklist
   DATABASE_URL=postgresql://solodit:your_secure_password@localhost:5432/solodit_checklist

   # Other configurations as before...
   ```

5. Setup Backend:
   ```bash
   cd backend
   pip3 install -r requirements.txt

   # Start backend service (using tmux for persistence)
   sudo yum install tmux -y
   tmux new-session -d -s backend 'python3 -m uvicorn main:app --host 0.0.0.0 --port 8000'
   ```

6. Setup Frontend:
   ```bash
   cd ../frontend
   npm install

   # Build for production
   npm run build

   # Install and configure nginx
   sudo yum install nginx -y
   sudo nano /etc/nginx/conf.d/solodit.conf
   ```
   Add nginx configuration:
   ```nginx
   server {
       listen 80;
       server_name your_ec2_domain_or_ip;

       # Serve frontend
       location / {
           root /home/ec2-user/solodit-checklist-matcher/frontend/build;
           try_files $uri $uri/ /index.html;
       }

       # Proxy backend API requests
       location /api/ {
           proxy_pass http://localhost:8000/;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```
   ```bash
   # Start nginx
   sudo systemctl start nginx
   sudo systemctl enable nginx
   ```

7. Setup Process Management (optional but recommended):
   ```bash
   # Install PM2 for process management
   npm install -g pm2

   # Start backend with PM2 (instead of tmux)
   cd ../backend
   pm2 start "python3 -m uvicorn main:app --host 0.0.0.0 --port 8000" --name solodit-backend

   # Save PM2 configuration
   pm2 save

   # Setup PM2 to start on boot
   pm2 startup
   ```

8. Setup SSL (recommended):
   ```bash
   # Install certbot
   sudo yum install certbot python3-certbot-nginx -y

   # Get SSL certificate
   sudo certbot --nginx -d your_domain.com
   ```

### Maintenance Tips

1. **Monitoring**:
   ```bash
   # Check backend logs
   pm2 logs solodit-backend

   # Check nginx logs
   sudo tail -f /var/log/nginx/error.log
   ```

2. **Updates**:
   ```bash
   # Update application
   cd ~/solodit-checklist-matcher
   git pull
   
   # Update backend
   cd backend
   pip3 install -r requirements.txt
   pm2 restart solodit-backend

   # Update frontend
   cd ../frontend
   npm install
   npm run build
   ```

3. **Backup**:
   ```bash
   # Backup database
   pg_dump -U solodit solodit_checklist > backup.sql
   ```

### Security Notes

1. Configure your EC2 security group carefully
2. Use strong passwords for PostgreSQL
3. Keep your system and dependencies updated
4. Consider setting up automated backups
5. Monitor system resources and logs
6. Use SSL/TLS for production deployments