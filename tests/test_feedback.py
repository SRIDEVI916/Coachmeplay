import os
import sys
import pytest
import jwt
from datetime import datetime, timedelta
import requests

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, mysql

class TestFeedback:
    @pytest.fixture
    def app(self):
        """Create and configure a test Flask app"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['MYSQL_HOST'] = 'localhost'  # Use local test DB
        app.config['MYSQL_USER'] = 'root'  # Update with your test DB credentials
        app.config['MYSQL_PASSWORD'] = ''
        app.config['MYSQL_DB'] = 'coachmeplay_test'
        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client"""
        return app.test_client()

    def create_token(self, app, user_data):
        """Helper to create JWT tokens for testing"""
        token = jwt.encode(
            {
                'user_id': user_data['user_id'],
                'user_type': user_data['user_type'],
                'email': user_data['email'],
                'exp': datetime.utcnow() + timedelta(days=1),
                'coach_id': user_data.get('coach_id')
            },
            app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
        return token

    def test_feedback_flow(self, app, client):
        """Integration test for the feedback creation and retrieval flow"""
        # Test data
        coach_data = {
            'user_id': 18,
            'user_type': 'coach',
            'email': 'coach@test.com',
            'coach_id': 2
        }
        athlete_data = {
            'user_id': 19,
            'user_type': 'athlete',
            'email': 'athlete@test.com'
        }

        # Create tokens
        coach_token = self.create_token(app, coach_data)
        athlete_token = self.create_token(app, athlete_data)

        # 1. Coach creates feedback
        feedback_data = {
            'athlete_id': 1,  # Test athlete ID
            'feedback_text': 'Great progress on strength training!',
            'performance_rating': 5,
            'focus_areas': 'Strength, Endurance',
            'strengths': 'Dedication, Form',
            'improvements_needed': 'Recovery time'
        }

        response = client.post(
            '/api/feedback/create',
            json=feedback_data,
            headers={'Authorization': f'Bearer {coach_token}'}
        )
        assert response.status_code == 201
        feedback_id = response.json['feedback_id']

        # 2. Coach retrieves given feedback
        response = client.get(
            f'/api/feedback/coach/{coach_data["coach_id"]}/given',
            headers={'Authorization': f'Bearer {coach_token}'}
        )
        assert response.status_code == 200
        assert len(response.json['feedbacks']) > 0

        # 3. Athlete retrieves received feedback
        response = client.get(
            f'/api/feedback/athlete/{athlete_data["user_id"]}/received',
            headers={'Authorization': f'Bearer {athlete_token}'}
        )
        assert response.status_code == 200

        # 4. Both can view feedback detail
        response = client.get(
            f'/api/feedback/{feedback_id}',
            headers={'Authorization': f'Bearer {coach_token}'}
        )
        assert response.status_code == 200

        response = client.get(
            f'/api/feedback/{feedback_id}',
            headers={'Authorization': f'Bearer {athlete_token}'}
        )
        assert response.status_code == 200

        # 5. Coach can delete feedback
        response = client.delete(
            f'/api/feedback/{feedback_id}',
            headers={'Authorization': f'Bearer {coach_token}'}
        )
        assert response.status_code == 200

        # Verify deletion
        response = client.get(
            f'/api/feedback/{feedback_id}',
            headers={'Authorization': f'Bearer {coach_token}'}
        )
        assert response.status_code == 404