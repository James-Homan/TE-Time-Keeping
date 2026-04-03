"""TE Timekeeping - Time Tracking Application.

This application helps employees track their time allocation across different
departments and factories using area logging and task/service logging.
"""

__version__ = "1.0.0"
__author__ = "Zachary Mangiafesto & James Homan"
__license__ = "MIT"

from APP import create_app

def get_app():
    """Get the Flask application instance."""
    return create_app()
