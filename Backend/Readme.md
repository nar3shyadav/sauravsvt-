# ROC Gym - Job Listing and Employee Management API

This is a Flask-based backend application for ROC Gym's recruitment and employee management system. It provides a RESTful API for managing job listings, user authentication, and role-based access control.

## Company

**ROC Gym** - Recruitment and Management of Fitness Centers

## Features

-   **User Authentication**: Secure user registration and JWT-based login for different roles.
-   **Role-Based Access Control**:
    -   **Admin**: Full CRUD operations on all job listings, can view all applications and member details.
    -   **Recruiter**: Can create, update, and delete their own job listings for specific gym branches, and view applications for their jobs.
    -   **Trainer/Employee (User)**: Can view jobs, update profiles, and apply for internal positions when authenticated.
    -   **Guest User (Unauthenticated)**: Can view job listings and general gym information.
-   **Job Management**: Endpoints for creating, retrieving, updating, and deleting jobs.
-   **Job Search**: Filter jobs by title, location, and work type.
-   **View Tracking**: Automatically tracks the number of views for each job listing.
-   **Job Applications**: Authenticated users can apply for jobs with resume and cover letter.
-   **Member Management**: Admin can view gym member details.
-   **Health Monitoring**: Health check endpoint for monitoring system status.

## API Endpoints

For a complete step-by-step testing guide with all endpoints and examples, see **[API_TESTING_GUIDE.md](./API_TESTING_GUIDE.md)**.

### Quick Reference

**Public Endpoints**:
- GET `/` - Home endpoint with API information
- GET `/health` - Health check endpoint (checks database connectivity)
- GET `/jobs` - Get all job listings with optional filtering (`?title=`, `?location=`, `?work_type=`)
- GET `/jobs/<id>` - Get a single job listing by ID (increments view count)

### Authentication Endpoints

- **POST `/auth/register`** - Register a new user
  ```json
  {
    "email": "user@example.com",
    "password": "password123",
    "role": "user" // or "admin", "recruiter"
  }
  ```

- **POST `/auth/login`** - Login and get JWT token
  ```json
  {
    "email": "user@example.com",
    "password": "password123"
  }
  ```
  Response: `{"token": "jwt_token_here"}`

- **POST `/auth/logout`** - Logout (requires authentication)
  - Headers: `Authorization: Bearer <token>`
  - Response: `{"message": "Successfully logged out. Please remove token from client."}`
  - Note: Client should remove token after logout

### Job Management Endpoints (Requires Authentication)

- **POST `/jobs`** - Create a new job listing (Admin/Recruiter only)
  - Headers: `Authorization: Bearer <token>`
  ```json
  {
    "title": "Fitness Trainer",
    "description": "Job responsibilities, qualifications, and experience required",
    "location": "Downtown",
    "work_type": "Full-time",
    "salary_range": "30000-45000",
    "requirements": "Certified Personal Trainer, CPR certified",
    "company_name": "ROC Gym"
  }
  ```

- **PUT `/jobs/<id>`** - Update a job listing (Admin/Recruiter only)
  - Admin can update any job
  - Recruiter can only update their own jobs

- **DELETE `/jobs/<id>`** - Delete a job listing (Admin/Recruiter only)
  - Admin can delete any job
  - Recruiter can only delete their own jobs

### Application Endpoints (Requires Authentication)

- **POST `/jobs/<id>/apply`** - Apply for a job (User role only)
  ```json
  {
    "full_name": "John Doe",
    "email": "john@example.com",
    "resume_url": "https://example.com/resume.pdf",
    "cover_letter": "Optional cover letter...",
    "additional_info": "Optional additional information"
  }
  ```

- **GET `/applications`** - Get applications
  - Users: Get their own applications
  - Admins: Get all applications
  - Recruiters: Get applications for their posted jobs

- **GET `/jobs/<id>/applications`** - Get all applications for a specific job (Admin/Recruiter only)
  - Admin can view applications for any job
  - Recruiter can only view applications for their own jobs

### Member Management Endpoints (Requires Authentication)

- **GET `/members`** - Get gym member details (Admin only)
  - Headers: `Authorization: Bearer <token>`
  - Returns list of all gym members

## Role-Based Permissions Summary

| Action | Guest | User (Trainer/Employee) | Recruiter | Admin |
|--------|-------|-------------------------|-----------|-------|
| View jobs | ✅ | ✅ | ✅ | ✅ |
| Apply for jobs | ❌ | ✅ | ❌ | ❌ |
| Create jobs | ❌ | ❌ | ✅ (own branch) | ✅ (all) |
| Update jobs | ❌ | ❌ | ✅ (own branch) | ✅ (all) |
| Delete jobs | ❌ | ❌ | ✅ (own branch) | ✅ (all) |
| View applications | ❌ | ✅ (own) | ✅ (own jobs) | ✅ (all) |
| View members | ❌ | ❌ | ❌ | ✅ |

## Project Structure

## Configuration

This app uses environment variables (loaded via `python-dotenv`) for configuration.

- Create a `.env` file in the project root by copying the provided example:

```bash
cp env.example .env
```

- Available variables:
  - `HOST` (default: `0.0.0.0`)
  - `PORT` (default: `5002`)
  - `DEBUG` (default: `false`) — set to `true` only for local development
  - `SECRET_KEY` — set a strong value in production
  - `MONGO_URI` — connection string for MongoDB (default: `mongodb://localhost:27017/`)
  - `DB_NAME` — database name (default: `roc_gym_db`)

## Running

### Development

```bash
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Production

- Use a production WSGI server such as `gunicorn` or `uwsgi`.
- Example with `gunicorn` (install it if needed):

```bash
pip install gunicorn
HOST=0.0.0.0 PORT=5002 DEBUG=false \
gunicorn -w 4 -b "$HOST:$PORT" app:app
```

Notes:
- Keep `DEBUG=false` in production.
- Manage secrets (like `SECRET_KEY`) via environment variables or a secrets manager.