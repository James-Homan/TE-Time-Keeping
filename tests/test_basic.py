"""Test suite for TE Timekeeping application."""

import pytest
from APP import create_app
from config import TestingConfig
from models import init_db, get_db, close_db


@pytest.fixture
def app():
    """Create and configure a test app instance."""
    app = create_app(TestingConfig)
    
    with app.app_context():
        init_db()
        yield app
        close_db()


@pytest.fixture
def client(app):
    """Test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Test CLI runner for the app."""
    return app.test_cli_runner()


class TestAuth:
    """Test authentication routes."""
    
    def test_login_page_loads(self, client):
        """Test that login page loads."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    def test_signup_creates_user(self, client):
        """Test that signup creates a new user."""
        response = client.post('/signup', data={
            'new_username': 'testuser',
            'new_password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_login_with_valid_credentials(self, client):
        """Test login with valid credentials."""
        # First create a user
        client.post('/signup', data={
            'new_username': 'testuser',
            'new_password': 'password123',
            'confirm_password': 'password123'
        })
        
        # Then login
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200


class TestModels:
    """Test database model functions."""
    
    def test_init_db_creates_tables(self, app):
        """Test that database initialization creates tables."""
        with app.app_context():
            db = get_db()
            cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            table_names = [row[0] for row in tables]
            
            assert 'user' in table_names
            assert 'charge_code' in table_names
            assert 'area' in table_names
            assert 'time_log' in table_names
            assert 'ts_log' in table_names


class TestAreaAndLogoutBehavior:
    """Test area logger refresh and auto-stop behavior on logout."""

    def test_area_logger_reflects_charge_code_updates(self, client, app):
        # Create a new user and login
        client.post('/signup', data={
            'new_username': 'areauser',
            'new_password': 'testpass123',
            'confirm_password': 'testpass123'
        }, follow_redirects=True)
        client.post('/login', data={'username': 'areauser', 'password': 'testpass123'}, follow_redirects=True)

        with app.app_context():
            db = get_db()
            # Update an existing charge code text to verify live reflection
            db.execute("UPDATE charge_code SET code = ? WHERE id = ?", ('VIG-60011-UPDATED', 1))
            db.commit()

        response = client.get('/area-logger')
        assert response.status_code == 200
        assert 'VIG-60011-UPDATED' in response.get_data(as_text=True)

    def test_logout_stops_active_area_and_ts_logs(self, client, app):
        client.post('/signup', data={
            'new_username': 'logoutuser',
            'new_password': 'testpass123',
            'confirm_password': 'testpass123'
        }, follow_redirects=True)
        client.post('/login', data={'username': 'logoutuser', 'password': 'testpass123'}, follow_redirects=True)

        # Start an area log for user
        response = client.post('/area-logger/', data={'action': 'start', 'area_id': '1'}, follow_redirects=True)
        assert response.status_code == 200

        # Start a TS log for user
        response = client.post('/ts-log/', data={
            'action': 'start',
            'task_name': 'Logout task',
            'description': 'logout test',
            'category': 'Testing',
            'priority': 'Low'
        }, follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            db = get_db()
            user = db.execute("SELECT id FROM user WHERE username = ?", ('logoutuser',)).fetchone()
            assert user
            user_id = user['id']
            active_area = db.execute("SELECT * FROM time_log WHERE user_id = ? AND end_time IS NULL", (user_id,)).fetchone()
            active_ts = db.execute("SELECT * FROM ts_log WHERE user_id = ? AND end_time IS NULL", (user_id,)).fetchone()
            assert active_area
            assert active_ts

        # Logout should stop both active logs
        client.get('/logout', follow_redirects=True)

        with app.app_context():
            db = get_db()
            active_area = db.execute("SELECT * FROM time_log WHERE user_id = ? AND end_time IS NULL", (user_id,)).fetchone()
            active_ts = db.execute("SELECT * FROM ts_log WHERE user_id = ? AND end_time IS NULL", (user_id,)).fetchone()
            assert active_area is None
            assert active_ts is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
