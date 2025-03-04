## Solodit Checklist Matcher
*Enhanced Tool for Security Audit Collaboration*

### **Core Functionality**
1. **Checklist Management**
   - Load checklist from [GitHub JSON](https://github.com/Cyfrin/audit-checklist/blob/main/checklist.json) on backend initialization.
   - Store checklist items in a **relational database** (e.g., PostgreSQL) with embeddings precomputed for semantic matching.
   - Database schema:
     ```sql
     CREATE TABLE checklist_items (
       id TEXT PRIMARY KEY,              -- e.g., "SOL-AM-DOSA-1"
       category TEXT,                    -- e.g., "Denial-Of-Service(DOS) Attack"
       question TEXT,
       description TEXT,
       remediation TEXT,
       references JSONB,                 -- Array of URLs
       embedding VECTOR(384)             -- Stored embeddings (using pgvector)
     );
     ```

2. **Resync Mechanism**
   - Add a "Resync Checklist" button in the frontend.
   - On click:
     - Fetch latest checklist from GitHub.
     - Compare items by `id` to detect new entries.
     - Add new items to the database (existing items remain unchanged).

---

### **Enhanced Features**
#### **1. Reference Contribution Workflow**
- **Frontend UI**:
  - Split left panel into two sections:
    - **Top**: Optional URL input field with "Load Content" button (auto-fetches text from link).
    - **Bottom**: Text area for issue writeup (pre-filled if URL content is loaded).
  - After matching checklist items, users can:
    - Select multiple items from results.
    - Click "Propose Reference Update" to store pending changes.

- **Pending Changes**:
  - Stored in a database table:
    ```sql
    CREATE TABLE pending_changes (
      change_id SERIAL PRIMARY KEY,
      checklist_item_id TEXT REFERENCES checklist_items(id),
      source_url TEXT NOT NULL,          -- Mandatory reference URL
      status TEXT DEFAULT 'pending',      -- e.g., pending/approved/rejected
      created_at TIMESTAMP DEFAULT NOW()
    );
    ```

#### **2. GitHub PR Automation**
- Add a "Create Pull Request" button in the frontend.
- On click:
  - Backend gathers all pending changes.
  - For each change:
    - Append `source_url` to the `references` array of the corresponding checklist item.
  - Generate a modified `checklist.json` with updated references.
  - Automatically create a GitHub PR to the [Cyfrin/audit-checklist](https://github.com/Cyfrin/audit-checklist) repo using GitHub’s API.

---

### **Tech Stack**
#### **Backend**
- **Language**: Python (FastAPI for REST API)
- **Database**: PostgreSQL + pgvector (for embeddings)
- **NLP**: `sentence-transformers/all-MiniLM-L6-v2` (lightweight embeddings)
- **GitHub Integration**: PyGithub library for PR automation

#### **Frontend**
- **Framework**: React.js (TypeScript)
- **UI Components**:
  - `react-markdown` for rendering checklist descriptions
  - `react-query` for API state management
- **Auth**: GitHub OAuth (for PR creation permissions)

---

### **Example Workflow**
1. **User submits issue writeup**:
   ```
   "Attackers can drain funds via unprotected withdraw() function."
   ```
2. **Tool matches**:
   - `SOL-AC-1` (Missing access control)
   - `SOL-RE-2` (Reentrancy risk)

3. **User actions**:
   - Selects both items.
   - Inputs source URL: `https://example.com/hack-report`.
   - Clicks "Propose Update" → change stored in DB.

4. **PR Creation**:
   - Backend modifies `checklist.json` to add the URL to both items’ `references`.
   - Creates PR titled: "Added 2 references via Solodit Matcher".

---

### **Key Requirements**
1. **Embedding Caching**:
   - Precompute embeddings during initial load/resync to avoid runtime latency.

2. **Atomic Operations**:
   - Use database transactions for resyncs to prevent partial updates.

3. **Security**:
   - Validate URLs (e.g., allow only HTTPS).
   - Rate-limit PR creation to prevent spam.

4. **Error Handling**:
   - Clear error messages for failed GitHub API calls (e.g., "PR failed: invalid permissions").
