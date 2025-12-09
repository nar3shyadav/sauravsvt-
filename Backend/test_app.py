import pytest
import json
from app import app
from db import get_db
from auth import hash_password
from bson import ObjectId
from datetime import datetime


@pytest.fixture
def client():
    """Test client fixture"""
    app.config['TESTING'] = True
    app.config['DB_NAME'] = 'roc_gym_test_db'
    with app.test_client() as client:
        yield client
    # Cleanup test database
    with app.app_context():
        db = get_db()
        db.client.drop_database('roc_gym_test_db')


@pytest.fixture
def admin_token(client):
    """Create admin user and return token"""
    with app.app_context():
        db = get_db()
        users = db.users
        users.delete_many({})
        users.insert_one({
            'email': 'admin@test.com',
            'password': hash_password('password'),
            'role': 'admin',
            'created_at': datetime.utcnow()
        })
    
    response = client.post('/auth/login',
                          data=json.dumps({'email': 'admin@test.com', 'password': 'password'}),
                          content_type='application/json')
    return json.loads(response.data)['token']


@pytest.fixture
def recruiter_token(client):
    """Create recruiter user and return token"""
    with app.app_context():
        db = get_db()
        users = db.users
        # Check if recruiter already exists
        if not users.find_one({'email': 'recruiter@test.com'}):
            users.insert_one({
                'email': 'recruiter@test.com',
                'password': hash_password('password'),
                'role': 'recruiter',
                'created_at': datetime.utcnow()
            })
    
    response = client.post('/auth/login',
                          data=json.dumps({'email': 'recruiter@test.com', 'password': 'password'}),
                          content_type='application/json')
    return json.loads(response.data)['token']


@pytest.fixture
def user_token(client):
    """Create regular user and return token"""
    with app.app_context():
        db = get_db()
        users = db.users
        # Check if user already exists
        if not users.find_one({'email': 'user@test.com'}):
            users.insert_one({
                'email': 'user@test.com',
                'password': hash_password('password'),
                'role': 'user',
                'created_at': datetime.utcnow()
            })
    
    response = client.post('/auth/login',
                          data=json.dumps({'email': 'user@test.com', 'password': 'password'}),
                          content_type='application/json')
    return json.loads(response.data)['token']


class TestPublicEndpoints:
    """Test public endpoints"""
    
    def test_home(self, client):
        response = client.get('/')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['company'] == 'ROC Gym'
        assert 'endpoints' in data
    
    def test_health_check(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['database'] == 'connected'
    
    def test_get_jobs_empty(self, client):
        response = client.get('/jobs')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_register_user(self, client):
        response = client.post('/auth/register',
                              data=json.dumps({
                                  'email': 'newuser@test.com',
                                  'password': 'password123',
                                  'role': 'user'
                              }),
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'user_id' in data
    
    def test_register_duplicate_email(self, client, admin_token):
        response = client.post('/auth/register',
                              data=json.dumps({
                                  'email': 'admin@test.com',
                                  'password': 'password123',
                                  'role': 'user'
                              }),
                              content_type='application/json')
        assert response.status_code == 409
    
    def test_register_invalid_role(self, client):
        response = client.post('/auth/register',
                              data=json.dumps({
                                  'email': 'invalid@test.com',
                                  'password': 'password123',
                                  'role': 'invalid_role'
                              }),
                              content_type='application/json')
        assert response.status_code == 400
    
    def test_login_success(self, client, admin_token):
        response = client.post('/auth/login',
                              data=json.dumps({
                                  'email': 'admin@test.com',
                                  'password': 'password'
                              }),
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'token' in data
    
    def test_login_wrong_password(self, client, admin_token):
        response = client.post('/auth/login',
                              data=json.dumps({
                                  'email': 'admin@test.com',
                                  'password': 'wrongpassword'
                              }),
                              content_type='application/json')
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client):
        response = client.post('/auth/login',
                              data=json.dumps({
                                  'email': 'nonexistent@test.com',
                                  'password': 'password'
                              }),
                              content_type='application/json')
        assert response.status_code == 401
    
    def test_logout(self, client, user_token):
        response = client.post('/auth/logout',
                              headers={'Authorization': f'Bearer {user_token}'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'logged out' in data['message'].lower()


class TestJobManagement:
    """Test job management endpoints"""
    
    def test_create_job_as_admin(self, client, admin_token):
        response = client.post('/jobs',
                              data=json.dumps({
                                  'title': 'Fitness Trainer',
                                  'description': 'Test job',
                                  'location': 'Downtown',
                                  'work_type': 'Full-time',
                                  'salary_range': '30000-45000',
                                  'requirements': 'CPR certified'
                              }),
                              headers={'Authorization': f'Bearer {admin_token}'},
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == 'Fitness Trainer'
        assert data['company_name'] == 'ROC Gym'
        assert data['views'] == 0
    
    def test_create_job_as_recruiter(self, client, recruiter_token):
        response = client.post('/jobs',
                              data=json.dumps({
                                  'title': 'Front Desk Executive',
                                  'description': 'Test job',
                                  'location': 'Central',
                                  'work_type': 'Part-time'
                              }),
                              headers={'Authorization': f'Bearer {recruiter_token}'},
                              content_type='application/json')
        assert response.status_code == 201
    
    def test_create_job_as_user_forbidden(self, client, user_token):
        response = client.post('/jobs',
                              data=json.dumps({
                                  'title': 'Test Job',
                                  'description': 'Test',
                                  'location': 'Test',
                                  'work_type': 'Full-time'
                              }),
                              headers={'Authorization': f'Bearer {user_token}'},
                              content_type='application/json')
        assert response.status_code == 403
    
    def test_create_job_missing_fields(self, client, admin_token):
        response = client.post('/jobs',
                              data=json.dumps({
                                  'title': 'Test Job'
                              }),
                              headers={'Authorization': f'Bearer {admin_token}'},
                              content_type='application/json')
        assert response.status_code == 400
    
    def test_get_all_jobs(self, client, admin_token):
        # Create a job first
        client.post('/jobs',
                   data=json.dumps({
                       'title': 'Fitness Trainer',
                       'description': 'Test',
                       'location': 'Downtown',
                       'work_type': 'Full-time'
                   }),
                   headers={'Authorization': f'Bearer {admin_token}'},
                   content_type='application/json')
        
        response = client.get('/jobs')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) > 0
    
    def test_get_job_by_id(self, client, admin_token):
        # Create a job
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Test Job',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {admin_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        # Get the job
        response = client.get(f'/jobs/{job_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['_id'] == job_id
        assert data['views'] == 1
    
    def test_get_job_invalid_id(self, client):
        response = client.get('/jobs/invalid_id')
        assert response.status_code == 400
    
    def test_get_job_not_found(self, client):
        fake_id = str(ObjectId())
        response = client.get(f'/jobs/{fake_id}')
        assert response.status_code == 404
    
    def test_update_job_as_admin(self, client, admin_token):
        # Create a job
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Original Title',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {admin_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        # Update the job
        response = client.put(f'/jobs/{job_id}',
                             data=json.dumps({'title': 'Updated Title'}),
                             headers={'Authorization': f'Bearer {admin_token}'},
                             content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == 'Updated Title'
    
    def test_update_job_recruiter_own(self, client, recruiter_token):
        # Create job as recruiter
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Original',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {recruiter_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        # Update own job
        response = client.put(f'/jobs/{job_id}',
                             data=json.dumps({'title': 'Updated'}),
                             headers={'Authorization': f'Bearer {recruiter_token}'},
                             content_type='application/json')
        assert response.status_code == 200
    
    def test_delete_job_as_admin(self, client, admin_token):
        # Create a job
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'To Delete',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {admin_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        # Delete the job
        response = client.delete(f'/jobs/{job_id}',
                                headers={'Authorization': f'Bearer {admin_token}'})
        assert response.status_code == 200


class TestJobApplications:
    """Test job application endpoints"""
    
    def test_apply_for_job(self, client, admin_token, user_token):
        # Create a job
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Test Job',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {admin_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        # Apply for job
        response = client.post(f'/jobs/{job_id}/apply',
                              data=json.dumps({
                                  'full_name': 'Test User',
                                  'email': 'test@test.com',
                                  'resume_url': 'http://test.com/resume.pdf'
                              }),
                              headers={'Authorization': f'Bearer {user_token}'},
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'application' in data
    
    def test_apply_duplicate(self, client, admin_token, user_token):
        # Create a job
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Test Job',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {admin_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        # Apply first time
        client.post(f'/jobs/{job_id}/apply',
                   data=json.dumps({
                       'full_name': 'Test User',
                       'email': 'test@test.com',
                       'resume_url': 'http://test.com/resume.pdf'
                   }),
                   headers={'Authorization': f'Bearer {user_token}'},
                   content_type='application/json')
        
        # Apply second time (should fail)
        response = client.post(f'/jobs/{job_id}/apply',
                              data=json.dumps({
                                  'full_name': 'Test User',
                                  'email': 'test@test.com',
                                  'resume_url': 'http://test.com/resume.pdf'
                              }),
                              headers={'Authorization': f'Bearer {user_token}'},
                              content_type='application/json')
        assert response.status_code == 409
    
    def test_apply_as_admin_forbidden(self, client, admin_token):
        # Create a job
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Test Job',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {admin_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        # Try to apply as admin (should fail)
        response = client.post(f'/jobs/{job_id}/apply',
                              data=json.dumps({
                                  'full_name': 'Admin',
                                  'email': 'admin@test.com',
                                  'resume_url': 'http://test.com/resume.pdf'
                              }),
                              headers={'Authorization': f'Bearer {admin_token}'},
                              content_type='application/json')
        assert response.status_code == 403
    
    def test_get_my_applications_as_user(self, client, admin_token, user_token):
        # Create and apply for a job
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Test Job',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {admin_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        client.post(f'/jobs/{job_id}/apply',
                   data=json.dumps({
                       'full_name': 'Test User',
                       'email': 'test@test.com',
                       'resume_url': 'http://test.com/resume.pdf'
                   }),
                   headers={'Authorization': f'Bearer {user_token}'},
                   content_type='application/json')
        
        # Get applications
        response = client.get('/applications',
                             headers={'Authorization': f'Bearer {user_token}'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] > 0
    
    def test_get_job_applications_as_admin(self, client, admin_token, user_token):
        # Create job and application
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Test Job',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {admin_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        client.post(f'/jobs/{job_id}/apply',
                   data=json.dumps({
                       'full_name': 'Test User',
                       'email': 'test@test.com',
                       'resume_url': 'http://test.com/resume.pdf'
                   }),
                   headers={'Authorization': f'Bearer {user_token}'},
                   content_type='application/json')
        
        # Get applications for job
        response = client.get(f'/jobs/{job_id}/applications',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] > 0


class TestMembers:
    """Test member management"""
    
    def test_get_members_as_admin(self, client, admin_token):
        response = client.get('/members',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'members' in data
        assert 'count' in data
    
    def test_get_members_as_user_forbidden(self, client, user_token):
        response = client.get('/members',
                             headers={'Authorization': f'Bearer {user_token}'})
        assert response.status_code == 403
    
    def test_get_members_as_recruiter_forbidden(self, client, recruiter_token):
        response = client.get('/members',
                             headers={'Authorization': f'Bearer {recruiter_token}'})
        assert response.status_code == 403


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_health_check_db_error(self, client, monkeypatch):
        """Test health check when database fails"""
        def mock_get_db():
            class MockDB:
                def command(self, cmd):
                    raise Exception("Database connection failed")
            return MockDB()
        
        with app.app_context():
            monkeypatch.setattr('app.get_db', mock_get_db)
            response = client.get('/health')
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data['status'] == 'unhealthy'
    
    def test_register_missing_fields(self, client):
        """Test registration with missing fields"""
        response = client.post('/auth/register',
                              data=json.dumps({'email': 'test@test.com'}),
                              content_type='application/json')
        assert response.status_code == 400
    
    def test_login_missing_fields(self, client):
        """Test login with missing fields"""
        response = client.post('/auth/login',
                              data=json.dumps({'email': 'test@test.com'}),
                              content_type='application/json')
        assert response.status_code == 400
    
    def test_apply_job_not_found(self, client, user_token):
        """Test applying for non-existent job"""
        fake_id = str(ObjectId())
        response = client.post(f'/jobs/{fake_id}/apply',
                              data=json.dumps({
                                  'full_name': 'Test',
                                  'email': 'test@test.com',
                                  'resume_url': 'http://test.com/resume.pdf'
                              }),
                              headers={'Authorization': f'Bearer {user_token}'},
                              content_type='application/json')
        assert response.status_code == 404
    
    def test_apply_missing_fields(self, client, admin_token, user_token):
        """Test applying with missing required fields"""
        # Create job first
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Test',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {admin_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        # Apply with missing fields
        response = client.post(f'/jobs/{job_id}/apply',
                              data=json.dumps({'full_name': 'Test'}),
                              headers={'Authorization': f'Bearer {user_token}'},
                              content_type='application/json')
        assert response.status_code == 400
    
    def test_update_job_not_found(self, client, admin_token):
        """Test updating non-existent job"""
        fake_id = str(ObjectId())
        response = client.put(f'/jobs/{fake_id}',
                             data=json.dumps({'title': 'Updated'}),
                             headers={'Authorization': f'Bearer {admin_token}'},
                             content_type='application/json')
        assert response.status_code == 404
    
    def test_update_job_invalid_id(self, client, admin_token):
        """Test updating with invalid job ID"""
        response = client.put('/jobs/invalid_id',
                             data=json.dumps({'title': 'Updated'}),
                             headers={'Authorization': f'Bearer {admin_token}'},
                             content_type='application/json')
        assert response.status_code == 400
    
    def test_delete_job_not_found(self, client, admin_token):
        """Test deleting non-existent job"""
        fake_id = str(ObjectId())
        response = client.delete(f'/jobs/{fake_id}',
                                headers={'Authorization': f'Bearer {admin_token}'})
        assert response.status_code == 404
    
    def test_delete_job_invalid_id(self, client, admin_token):
        """Test deleting with invalid job ID"""
        response = client.delete('/jobs/invalid_id',
                                headers={'Authorization': f'Bearer {admin_token}'})
        assert response.status_code == 400
    
    def test_get_job_applications_not_found(self, client, admin_token):
        """Test getting applications for non-existent job"""
        fake_id = str(ObjectId())
        response = client.get(f'/jobs/{fake_id}/applications',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert response.status_code == 404
    
    def test_get_job_applications_invalid_id(self, client, admin_token):
        """Test getting applications with invalid job ID"""
        response = client.get('/jobs/invalid_id/applications',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert response.status_code == 400
    
    def test_apply_invalid_job_id(self, client, user_token):
        """Test applying with invalid job ID"""
        response = client.post('/jobs/invalid_id/apply',
                              data=json.dumps({
                                  'full_name': 'Test',
                                  'email': 'test@test.com',
                                  'resume_url': 'http://test.com/resume.pdf'
                              }),
                              headers={'Authorization': f'Bearer {user_token}'},
                              content_type='application/json')
        assert response.status_code == 400
    
    def test_recruiter_view_applications(self, client, recruiter_token, user_token):
        """Test recruiter viewing applications for their jobs"""
        # Create job as recruiter
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Recruiter Job',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {recruiter_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        # Apply for job
        client.post(f'/jobs/{job_id}/apply',
                   data=json.dumps({
                       'full_name': 'Test User',
                       'email': 'test@test.com',
                       'resume_url': 'http://test.com/resume.pdf'
                   }),
                   headers={'Authorization': f'Bearer {user_token}'},
                   content_type='application/json')
        
        # Recruiter views applications
        response = client.get('/applications',
                             headers={'Authorization': f'Bearer {recruiter_token}'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] >= 1
    
    def test_recruiter_cannot_view_other_job_applications(self, client, admin_token, recruiter_token):
        """Test recruiter cannot view applications for jobs they didn't post"""
        # Admin creates job
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Admin Job',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {admin_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        # Recruiter tries to view applications
        response = client.get(f'/jobs/{job_id}/applications',
                             headers={'Authorization': f'Bearer {recruiter_token}'})
        assert response.status_code == 403
    
    def test_recruiter_cannot_update_other_jobs(self, client, admin_token, recruiter_token):
        """Test recruiter cannot update jobs they didn't create"""
        # Admin creates job
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Admin Job',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {admin_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        # Recruiter tries to update
        response = client.put(f'/jobs/{job_id}',
                             data=json.dumps({'title': 'Updated'}),
                             headers={'Authorization': f'Bearer {recruiter_token}'},
                             content_type='application/json')
        assert response.status_code == 403
    
    def test_recruiter_cannot_delete_other_jobs(self, client, admin_token, recruiter_token):
        """Test recruiter cannot delete jobs they didn't create"""
        # Admin creates job
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Admin Job',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {admin_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        # Recruiter tries to delete
        response = client.delete(f'/jobs/{job_id}',
                                headers={'Authorization': f'Bearer {recruiter_token}'})
        assert response.status_code == 403
    
    def test_missing_authorization_header(self, client):
        """Test endpoints without authorization header"""
        response = client.post('/jobs',
                              data=json.dumps({
                                  'title': 'Test',
                                  'description': 'Test',
                                  'location': 'Test',
                                  'work_type': 'Full-time'
                              }),
                              content_type='application/json')
        assert response.status_code == 401
    
    def test_invalid_token(self, client):
        """Test with invalid token"""
        response = client.post('/jobs',
                              data=json.dumps({
                                  'title': 'Test',
                                  'description': 'Test',
                                  'location': 'Test',
                                  'work_type': 'Full-time'
                              }),
                              headers={'Authorization': 'Bearer invalid_token'},
                              content_type='application/json')
        assert response.status_code == 401
    
    def test_expired_token(self, client, admin_token):
        """Test with expired token"""
        import jwt
        from datetime import datetime, timedelta
        
        # Create an expired token
        with app.app_context():
            expired_token = jwt.encode({
                'user_id': 'test_user_id',
                'role': 'admin',
                'exp': datetime.utcnow() - timedelta(hours=1)
            }, app.config['SECRET_KEY'], algorithm="HS256")
        
        response = client.post('/jobs',
                              data=json.dumps({
                                  'title': 'Test',
                                  'description': 'Test',
                                  'location': 'Test',
                                  'work_type': 'Full-time'
                              }),
                              headers={'Authorization': f'Bearer {expired_token}'},
                              content_type='application/json')
        assert response.status_code == 401
    
    def test_token_with_nonexistent_user(self, client):
        """Test token with user that doesn't exist in DB"""
        import jwt
        from datetime import datetime, timedelta
        
        fake_user_id = str(ObjectId())
        
        with app.app_context():
            fake_token = jwt.encode({
                'user_id': fake_user_id,
                'role': 'admin',
                'exp': datetime.utcnow() + timedelta(hours=1)
            }, app.config['SECRET_KEY'], algorithm="HS256")
        
        response = client.post('/jobs',
                              data=json.dumps({
                                  'title': 'Test',
                                  'description': 'Test',
                                  'location': 'Test',
                                  'work_type': 'Full-time'
                              }),
                              headers={'Authorization': f'Bearer {fake_token}'},
                              content_type='application/json')
        assert response.status_code == 401
    
    def test_update_job_no_changes(self, client, admin_token):
        """Test updating job with same data (no changes)"""
        # Create a job
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Test Job',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {admin_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        # Update with same data (should return no changes)
        response = client.put(f'/jobs/{job_id}',
                             data=json.dumps({}),
                             headers={'Authorization': f'Bearer {admin_token}'},
                             content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        # Could be "No changes made" or the job itself
        assert 'message' in data or 'title' in data
    
    def test_admin_view_all_applications(self, client, admin_token, user_token):
        """Test admin viewing all applications from all users"""
        # Create job and application
        create_response = client.post('/jobs',
                                     data=json.dumps({
                                         'title': 'Test',
                                         'description': 'Test',
                                         'location': 'Test',
                                         'work_type': 'Full-time'
                                     }),
                                     headers={'Authorization': f'Bearer {admin_token}'},
                                     content_type='application/json')
        job_id = json.loads(create_response.data)['_id']
        
        client.post(f'/jobs/{job_id}/apply',
                   data=json.dumps({
                       'full_name': 'Test User',
                       'email': 'test@test.com',
                       'resume_url': 'http://test.com/resume.pdf'
                   }),
                   headers={'Authorization': f'Bearer {user_token}'},
                   content_type='application/json')
        
        # Admin views ALL applications
        response = client.get('/applications',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'applications' in data
        assert 'count' in data
    
    def test_unknown_role_applications(self, client):
        """Test applications endpoint with unknown role"""
        import jwt
        from datetime import datetime, timedelta
        
        # Create user with unknown role
        with app.app_context():
            db = get_db()
            users = db.users
            result = users.insert_one({
                'email': 'unknown@test.com',
                'password': hash_password('password'),
                'role': 'guest',  # Unknown role
                'created_at': datetime.utcnow()
            })
            
            # Create token manually
            token = jwt.encode({
                'user_id': str(result.inserted_id),
                'role': 'guest',
                'exp': datetime.utcnow() + timedelta(hours=1)
            }, app.config['SECRET_KEY'], algorithm="HS256")
        
        # Try to get applications with unknown role
        response = client.get('/applications',
                             headers={'Authorization': f'Bearer {token}'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] == 0  # Should return empty for unknown roles
    


class TestJobFiltering:
    """Test job filtering"""
    
    def test_filter_by_title(self, client, admin_token):
        # Create jobs
        client.post('/jobs',
                   data=json.dumps({
                       'title': 'Fitness Trainer',
                       'description': 'Test',
                       'location': 'Downtown',
                       'work_type': 'Full-time'
                   }),
                   headers={'Authorization': f'Bearer {admin_token}'},
                   content_type='application/json')
        
        client.post('/jobs',
                   data=json.dumps({
                       'title': 'Front Desk Executive',
                       'description': 'Test',
                       'location': 'Central',
                       'work_type': 'Part-time'
                   }),
                   headers={'Authorization': f'Bearer {admin_token}'},
                   content_type='application/json')
        
        # Filter by title
        response = client.get('/jobs?title=Fitness')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) >= 1
        assert 'Fitness' in data[0]['title']
    
    def test_filter_by_location(self, client, admin_token):
        client.post('/jobs',
                   data=json.dumps({
                       'title': 'Test Job',
                       'description': 'Test',
                       'location': 'Downtown',
                       'work_type': 'Full-time'
                   }),
                   headers={'Authorization': f'Bearer {admin_token}'},
                   content_type='application/json')
        
        response = client.get('/jobs?location=Downtown')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) >= 1
    
    def test_filter_by_work_type(self, client, admin_token):
        client.post('/jobs',
                   data=json.dumps({
                       'title': 'Test Job',
                       'description': 'Test',
                       'location': 'Test',
                       'work_type': 'Full-time'
                   }),
                   headers={'Authorization': f'Bearer {admin_token}'},
                   content_type='application/json')
        
        response = client.get('/jobs?work_type=Full-time')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) >= 1

