# GitVlame API Documentation

## Authentication (`/auth`)

### 1. GitHub Login
- **URL**: `/auth/github/login`
- **Method**: `GET`
- **Description**: Redirects the user to GitHub's OAuth authorization page.
- **Response**: `307 Temporary Redirect`

### 2. GitHub Callback
- **URL**: `/auth/github/callback`
- **Method**: `GET`
- **Query Params**: 
  - `code`: GitHub authorization code
- **Description**: Handles the callback from GitHub, exchanges code for token, creates/updates user, and returns JWT.
- **Response**: Redirects to Frontend with `?token=JWT_TOKEN`

### 3. Get Current User
- **URL**: `/auth/me`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <token>`
- **Response Keys**: `id`, `username`, `avatar_url`, `created_at`

### 4. Logout
- **URL**: `/auth/logout`
- **Method**: `POST`
- **Description**: Logs out the user (Client should discard the token).

---

## GitHub Data (`/github`)

### 5. List Repositories
- **URL**: `/github/repos`
- **Method**: `GET`
- **Query Params**:
  - `page` (default: 1)
  - `per_page` (default: 30)
  - `sort` (default: "updated")
- **Description**: Lists repositories accessible by the logged-in user.

### 6. Get Contributors
- **URL**: `/github/repos/{owner}/{repo}/contributors`
- **Method**: `GET`
- **Description**: Gets contribution statistics for a repository.

### 7. Get Commits
- **URL**: `/github/repos/{owner}/{repo}/commits`
- **Method**: `GET`
- **Query Params**:
  - `path`: Filter by file path
  - `since`: Filter by date (ISO string)
- **Description**: Lists recent commits, optionally filtered by file path.

---

## Judgments (Complaints) (`/judgments`)

### 8. Create Judgment (File Complaint)
- **URL**: `/judgments`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "repo_owner": "string",
    "repo_name": "string",
    "title": "string",
    "description": "string",
    "file_path": "string",
    "period_days": 7
  }
  ```
- **Description**: Creates a new judgment case against a specific file/feature.
- **Response**: Created Judgment object with `case_number` (YYYY-XXXX-XXXX-XXXX).

### 9. List Judgments
- **URL**: `/judgments`
- **Method**: `GET`
- **Query Params**: `status`, `page`, `per_page`
- **Description**: Lists judgments filed by the current user.

### 10. Get Judgment Detail
- **URL**: `/judgments/{judgment_id}`
- **Method**: `GET`
- **Description**: Gets detailed info including suspects and blame results.

### 11. Analyze Suspects (AI)
- **URL**: `/judgments/{judgment_id}/analyze`
- **Method**: `POST`
- **Description**: **[Core Feature]** Triggers Gemini AI to analyze commit history, identify suspects, and calculate responsibility ratios.
- **Response**: Judgment object with populated `suspects` list.

### 12. Delete Judgment
- **URL**: `/judgments/{judgment_id}`
- **Method**: `DELETE`

---

## Blame & Verdict (`/judgments/{judgment_id}/blame`)

### 13. Create Blame Verdict
- **URL**: `/judgments/{judgment_id}/blame`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "intensity": "mild" | "medium" | "spicy"
  }
  ```
- **Description**: Generates a final verdict message for the main suspect using AI.
  - `mild`: Polite request
  - `medium`: Humorous/Witty
  - `spicy`: Direct/Aggressive
- **Response**: Blame object with generated `message`.

### 14. Get Blame Verdict
- **URL**: `/judgments/{judgment_id}/blame`
- **Method**: `GET`
- **Description**: Gets the existing verdict.

### 15. Generate Blame Image
- **URL**: `/judgments/{judgment_id}/blame/image`
- **Method**: `POST`
- **Description**: Generates a shareable card image with the verdict and suspect's avatar.
- **Response**: `{"image_url": "..."}`

---

## Models

### User
- `id`: UUID
- `username`: String
- `avatar_url`: String

### Judgment
- `id`: UUID
- `case_number`: String (Unique)
- `repo_name`: String
- `title`: String
- `status`: "pending" | "completed"
- `suspects`: List[Suspect]

### Suspect
- `username`: String
- `responsibility`: Integer (0-100)
- `reason`: String (AI generated reason)

### Blame
- `target_username`: String
- `message`: String (AI generated message)
- `intensity`: String
- `image_url`: String
