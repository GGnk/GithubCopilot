"""
Test suite for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, reset_activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset activities state before each test"""
    reset_activities()
    yield


class TestGetActivities:
    """Tests for the GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that we can fetch all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Check that we have all activities
        assert len(data) == 9
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Basketball Team" in data

    def test_get_activities_has_required_fields(self, client):
        """Test that activities have all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        # Check one activity has all required fields
        chess = data["Chess Club"]
        assert "description" in chess
        assert "schedule" in chess
        assert "max_participants" in chess
        assert "participants" in chess

    def test_get_activities_shows_participant_list(self, client):
        """Test that activities show current participants"""
        response = client.get("/activities")
        data = response.json()
        
        chess = data["Chess Club"]
        assert len(chess["participants"]) == 2
        assert "michael@mergington.edu" in chess["participants"]
        assert "daniel@mergington.edu" in chess["participants"]


class TestSignup:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""

    def test_signup_successful(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Tennis%20Club/signup?email=new_student@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "new_student@mergington.edu" in data["message"]

    def test_signup_adds_participant(self, client):
        """Test that signup actually adds the participant"""
        email = "new_student@mergington.edu"
        
        # Signup
        client.post(f"/activities/Tennis%20Club/signup?email={email}")
        
        # Verify
        response = client.get("/activities")
        data = response.json()
        assert email in data["Tennis Club"]["participants"]

    def test_signup_nonexistent_activity(self, client):
        """Test signup fails for nonexistent activity"""
        response = client.post(
            "/activities/Nonexistent%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_duplicate_student(self, client):
        """Test that a student can't sign up twice for the same activity"""
        email = "michael@mergington.edu"
        response = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_multiple_activities(self, client):
        """Test that a student can sign up for multiple activities"""
        email = "multi_student@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Sign up for Programming Class
        response2 = client.post(
            f"/activities/Programming%20Class/signup?email={email}"
        )
        assert response2.status_code == 200
        
        # Verify both signups
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]
        assert email in data["Programming Class"]["participants"]


class TestUnregister:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_successful(self, client):
        """Test successful unregistration from an activity"""
        email = "michael@mergington.edu"
        response = client.delete(
            f"/activities/Chess%20Club/unregister?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]

    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes the participant"""
        email = "michael@mergington.edu"
        
        # Verify participant exists
        response = client.get("/activities")
        assert email in response.json()["Chess Club"]["participants"]
        
        # Unregister
        client.delete(f"/activities/Chess%20Club/unregister?email={email}")
        
        # Verify removal
        response = client.get("/activities")
        assert email not in response.json()["Chess Club"]["participants"]

    def test_unregister_nonexistent_activity(self, client):
        """Test unregister fails for nonexistent activity"""
        response = client.delete(
            "/activities/Nonexistent%20Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_not_signed_up(self, client):
        """Test that unregister fails if student not signed up"""
        response = client.delete(
            "/activities/Tennis%20Club/unregister?email=not_signed_up@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_unregister_then_signup_again(self, client):
        """Test that a student can sign up again after unregistering"""
        email = "michael@mergington.edu"
        
        # Unregister
        client.delete(f"/activities/Chess%20Club/unregister?email={email}")
        
        # Sign up again
        response = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        assert email in response.json()["Chess Club"]["participants"]


class TestAvailability:
    """Tests for availability/spots tracking"""

    def test_spots_left_calculation(self, client):
        """Test that spots left are calculated correctly"""
        response = client.get("/activities")
        data = response.json()
        
        chess = data["Chess Club"]
        spots_left = chess["max_participants"] - len(chess["participants"])
        # Chess Club has 12 max, 2 participants, so 10 spots left
        assert spots_left == 10

    def test_spots_decrease_after_signup(self, client):
        """Test that spots decrease when someone signs up"""
        # Get initial spots
        response = client.get("/activities")
        initial_spots = (
            response.json()["Tennis Club"]["max_participants"] -
            len(response.json()["Tennis Club"]["participants"])
        )
        
        # Sign up a new student
        client.post("/activities/Tennis%20Club/signup?email=new@mergington.edu")
        
        # Get updated spots
        response = client.get("/activities")
        updated_spots = (
            response.json()["Tennis Club"]["max_participants"] -
            len(response.json()["Tennis Club"]["participants"])
        )
        
        assert updated_spots == initial_spots - 1

    def test_spots_increase_after_unregister(self, client):
        """Test that spots increase when someone unregisters"""
        # Sign up a student
        client.post("/activities/Tennis%20Club/signup?email=new@mergington.edu")
        
        # Get spots after signup
        response = client.get("/activities")
        spots_after_signup = (
            response.json()["Tennis Club"]["max_participants"] -
            len(response.json()["Tennis Club"]["participants"])
        )
        
        # Unregister
        client.delete(
            "/activities/Tennis%20Club/unregister?email=new@mergington.edu"
        )
        
        # Get spots after unregister
        response = client.get("/activities")
        spots_after_unregister = (
            response.json()["Tennis Club"]["max_participants"] -
            len(response.json()["Tennis Club"]["participants"])
        )
        
        assert spots_after_unregister == spots_after_signup + 1


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]
