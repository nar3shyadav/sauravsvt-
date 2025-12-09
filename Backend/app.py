import os
from flask import Flask, jsonify, request, make_response, g
from bson import ObjectId
from datetime import datetime
from dotenv import load_dotenv

from db import get_db, close_db
from auth import setup_auth_routes, token_required, roles_required

load_dotenv()

app = Flask(__name__)

# --- Configuration ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_default_secret_key')
app.config['MONGO_URI'] = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
app.config['DB_NAME'] = os.environ.get('DB_NAME', 'roc_gym_db')


# Register teardown function to close DB connection
app.teardown_appcontext(close_db)

# --- Helper Function ---
def serialize_doc(doc):
    """Converts a MongoDB doc to a JSON-serializable format."""
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    if 'job_id' in doc and isinstance(doc['job_id'], ObjectId):
        doc['job_id'] = str(doc['job_id'])
    return doc

# --- Setup Authentication Routes ---
setup_auth_routes(app)


# --- Home and Health Endpoints ---

@app.route("/", methods=["GET"])
def home():
    """Home endpoint providing API information"""
    return make_response(jsonify({
        "message": "ROC Gym - Job Listing and Employee Management API",
        "company": "ROC Gym",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "auth": {
                "register": "/auth/register",
                "login": "/auth/login",
                "logout": "/auth/logout"
            },
            "jobs": {
                "list": "/jobs",
                "get": "/jobs/<id>",
                "create": "/jobs (POST, requires auth: admin/recruiter)",
                "update": "/jobs/<id> (PUT, requires auth: admin/recruiter)",
                "delete": "/jobs/<id> (DELETE, requires auth: admin/recruiter)",
                "apply": "/jobs/<id>/apply (POST, requires auth: user)",
                "applications": "/jobs/<id>/applications (GET, requires auth: admin/recruiter)"
            },
            "applications": {
                "my_applications": "/applications (GET, requires auth)"
            },
            "members": {
                "list": "/members (GET, requires auth: admin)"
            }
        }
    }), 200)

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring"""
    try:
        db = get_db()
        # Test database connection
        db.command('ping')
        return make_response(jsonify({
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }), 200)
    except Exception as e:
        return make_response(jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 503)


# --- Job API Endpoints ---

@app.route("/jobs", methods=["POST"])
@token_required
@roles_required('admin', 'recruiter')
def create_job():
    """Create a new job listing (Admin/Recruiter only)"""
    data = request.get_json()
    db = get_db()
    jobs_collection = db.jobs

    required_fields = ["title", "description", "location", "work_type"]
    if not all(field in data for field in required_fields):
        return make_response(jsonify({"error": "Missing required job fields"}), 400)

    new_job = {
        "company_name": data.get("company_name", "ROC Gym"),
        "title": data["title"],
        "description": data["description"],
        "location": data["location"],
        "work_type": data["work_type"],
        "salary_range": data.get("salary_range", ""),
        "requirements": data.get("requirements", ""),
        "views": 0,
        "date_posted": datetime.utcnow(),
        "posted_by": g.current_user_id # Link job to the user who posted it
    }

    result = jobs_collection.insert_one(new_job)
    created_job = jobs_collection.find_one({"_id": result.inserted_id})
    return make_response(jsonify(serialize_doc(created_job)), 201)

@app.route("/jobs", methods=["GET"])
def get_all_jobs():
    """Retrieve all job listings with filtering"""
    db = get_db()
    jobs_collection = db.jobs
    
    query = {}
    title = request.args.get('title')
    location = request.args.get('location')
    work_type = request.args.get('work_type')

    if title:
        query['title'] = {'$regex': title, '$options': 'i'}
    if location:
        query['location'] = {'$regex': location, '$options': 'i'}
    if work_type:
        query['work_type'] = work_type

    all_jobs = [serialize_doc(job) for job in jobs_collection.find(query)]
    return make_response(jsonify(all_jobs), 200)

@app.route("/jobs/<string:job_id>", methods=["GET"])
def get_job_by_id(job_id):
    """Retrieve a single job listing by ID and increment views"""
    db = get_db()
    jobs_collection = db.jobs
    
    try:
        # Increment the view count
        result = jobs_collection.find_one_and_update(
            {"_id": ObjectId(job_id)},
            {"$inc": {"views": 1}},
            return_document=True
        )
        if result:
            return make_response(jsonify(serialize_doc(result)), 200)
        else:
            return make_response(jsonify({"error": "Job not found"}), 404)
    except Exception:
        return make_response(jsonify({"error": "Invalid job ID format"}), 400)

@app.route("/jobs/<string:job_id>", methods=["PUT"])
@token_required
@roles_required('admin', 'recruiter')
def update_job(job_id):
    """Update an existing job listing"""
    data = request.get_json()
    db = get_db()
    jobs_collection = db.jobs

    try:
        job = jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            return make_response(jsonify({"error": "Job not found"}), 404)

        # Check permissions: Admin can edit any job, Recruiter can only edit their own.
        if g.current_user_role == 'recruiter' and job.get('posted_by') != g.current_user_id:
            return make_response(jsonify({"error": "Permission denied: You can only update jobs you have posted"}), 403)

        # Always set updated_by and updated_at on an update
        data['updated_by'] = g.current_user_id
        data['updated_at'] = datetime.utcnow()

        update_result = jobs_collection.update_one({"_id": ObjectId(job_id)}, {"$set": data})
        if update_result.modified_count > 0:
            updated_job = jobs_collection.find_one({"_id": ObjectId(job_id)})
            return make_response(jsonify(serialize_doc(updated_job)), 200)
        return make_response(jsonify({"message": "No changes made"}), 200)
    except Exception:
        return make_response(jsonify({"error": "Invalid job ID format"}), 400)


@app.route("/jobs/<string:job_id>", methods=["DELETE"])
@token_required
@roles_required('admin', 'recruiter')
def delete_job(job_id):
    """Delete a job listing"""
    db = get_db()
    jobs_collection = db.jobs

    try:
        job = jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            return make_response(jsonify({"error": "Job not found"}), 404)
        
        # Admin can delete any job, Recruiter only their own
        if g.current_user_role == 'recruiter' and job.get('posted_by') != g.current_user_id:
            return make_response(jsonify({"error": "Permission denied"}), 403)

        result = jobs_collection.delete_one({"_id": ObjectId(job_id)})
        if result.deleted_count > 0:
            return make_response(jsonify({"message": "Job deleted successfully"}), 200)
        else:
            return make_response(jsonify({"error": "Job not found"}), 404)
    except Exception:
        return make_response(jsonify({"error": "Invalid job ID format"}), 400)


@app.route("/jobs/<string:job_id>/apply", methods=["POST"])
@token_required
def apply_for_job(job_id):
    """Apply for a job (Authenticated users only)"""
    # Only 'user' role can apply for jobs (not admin or recruiter)
    if g.current_user_role != 'user':
        return make_response(jsonify({
            "error": "Only regular users can apply for jobs. Admins and recruiters cannot apply."
        }), 403)
    
    data = request.get_json()
    db = get_db()
    jobs_collection = db.jobs
    applications_collection = db.applications
    
    try:
        # Check if job exists
        job = jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            return make_response(jsonify({"error": "Job not found"}), 404)
        
        # Check if user has already applied for this job
        existing_application = applications_collection.find_one({
            "job_id": ObjectId(job_id),
            "applicant_id": g.current_user_id
        })
        if existing_application:
            return make_response(jsonify({
                "error": "You have already applied for this job"
            }), 409)
        
        # Create application
        required_fields = ["full_name", "email", "resume_url"]  # resume_url can be a URL or file path
        if not all(field in data for field in required_fields):
            return make_response(jsonify({
                "error": "Missing required fields: full_name, email, resume_url"
            }), 400)
        
        new_application = {
            "job_id": ObjectId(job_id),
            "applicant_id": g.current_user_id,
            "full_name": data["full_name"],
            "email": data["email"],
            "resume_url": data["resume_url"],
            "cover_letter": data.get("cover_letter", ""),
            "additional_info": data.get("additional_info", ""),
            "status": "pending",  # pending, reviewed, accepted, rejected
            "applied_at": datetime.utcnow()
        }
        
        result = applications_collection.insert_one(new_application)
        created_application = applications_collection.find_one({"_id": result.inserted_id})
        
        return make_response(jsonify({
            "message": "Application submitted successfully",
            "application": serialize_doc(created_application)
        }), 201)
        
    except Exception as e:
        return make_response(jsonify({
            "error": "Invalid job ID format" if "Invalid" in str(e) else str(e)
        }), 400)


@app.route("/jobs/<string:job_id>/applications", methods=["GET"])
@token_required
@roles_required('admin', 'recruiter')
def get_job_applications(job_id):
    """Get all applications for a specific job (Admin/Recruiter only)"""
    db = get_db()
    jobs_collection = db.jobs
    applications_collection = db.applications
    
    try:
        # Check if job exists
        job = jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            return make_response(jsonify({"error": "Job not found"}), 404)
        
        # Recruiters can only view applications for their own jobs
        if g.current_user_role == 'recruiter' and job.get('posted_by') != g.current_user_id:
            return make_response(jsonify({
                "error": "Permission denied: You can only view applications for jobs you have posted"
            }), 403)
        
        # Get all applications for this job
        applications = list(applications_collection.find({"job_id": ObjectId(job_id)}))
        
        return make_response(jsonify({
            "job_id": job_id,
            "applications": [serialize_doc(app) for app in applications],
            "count": len(applications)
        }), 200)
        
    except Exception:
        return make_response(jsonify({"error": "Invalid job ID format"}), 400)


@app.route("/applications", methods=["GET"])
@token_required
def get_my_applications():
    """Get all applications submitted by the current user"""
    db = get_db()
    applications_collection = db.applications
    
    try:
        # Users can only view their own applications
        if g.current_user_role == 'user':
            applications = list(applications_collection.find({"applicant_id": g.current_user_id}))
        # Admins can view all applications, recruiters can view applications for their jobs
        elif g.current_user_role == 'admin':
            applications = list(applications_collection.find({}))
        elif g.current_user_role == 'recruiter':
            # Get jobs posted by this recruiter
            jobs_collection = db.jobs
            my_jobs = jobs_collection.find({"posted_by": g.current_user_id})
            my_job_ids = [ObjectId(str(job['_id'])) for job in my_jobs]
            applications = list(applications_collection.find({
                "job_id": {"$in": my_job_ids}
            }))
        else:
            applications = []
        
        return make_response(jsonify({
            "applications": [serialize_doc(app) for app in applications],
            "count": len(applications)
        }), 200)
        
    except Exception as e:
        return make_response(jsonify({"error": str(e)}), 500)


# --- Members API Endpoint ---

@app.route("/members", methods=["GET"])
@token_required
@roles_required('admin')
def get_members():
    """Retrieve gym member details (Admin only)"""
    db = get_db()
    members_collection = db.members
    
    try:
        # Get all members
        members = list(members_collection.find({}))
        
        return make_response(jsonify({
            "members": [serialize_doc(member) for member in members],
            "count": len(members)
        }), 200)
        
    except Exception as e:
        return make_response(jsonify({"error": str(e)}), 500)


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5002"))
    debug = os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes", "on")
    app.run(host=host, port=port, debug=debug)