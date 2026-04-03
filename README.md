# TE Timekeeping Application

A professional time tracking application for T&E (Test and Evaluation) departments to allocate employee time across different factories, departments, and projects.

## Overview

This Flask-based web application provides:
- **Area Logging**: Track time spent in different work areas/factories
- **Task/Service Logging**: Log time spent on specific tasks or services
- **Timecard Summary**: View aggregated time allocation by area and charge code
- **Management Console**: Administer charge codes and work areas
- **User Authentication**: Secure login with password hashing

### Features

- ✅ Real-time time tracking with active log management
- ✅ Date range filtering and reporting
- ✅ CSV export functionality
- ✅ Charge code integration for project/department tracking
- ✅ User authentication and session management
- ✅ Responsive web interface
- ✅ Comprehensive logging and error handling
- ✅ Security headers and best practices

## Technology Stack

- **Backend**: Flask 3.0.0, SQLite, Python 3.8+
- **Frontend**: HTML/CSS/JavaScript with Chart.js for visualizations
- **Database**: SQLite with proper schema and relationships
- **Security**: Werkzeug password hashing, session management, security headers

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Virtual environment (recommended)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/zmanja42-ai/Time-Card-Management.git
cd Time-Card-Management
```

### 2. Create Virtual Environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables

Create a `.env` file in the root directory (optional, has defaults):

```env
FLASK_ENV=development
DEBUG=False
SECRET_KEY=your-secret-key-here
LOG_LEVEL=INFO
SESSION_COOKIE_SECURE=False
```

**Production settings:**
```env
FLASK_ENV=production
DEBUG=False
SECRET_KEY=your-production-secret-key
SESSION_COOKIE_SECURE=True
LOG_LEVEL=WARNING
```

### 5. Run the Application

```bash
python APP.py
```

The application will be available at `http://localhost:5000`

## Usage

### First Time Setup

1. Navigate to `http://localhost:5000/login`
2. Click to create a new account
3. Enter username and password (8+ characters)
4. Log in with your credentials

### Logging Time by Area

1. Go to **Area Logger** from the dashboard
2. Select an area/factory from the dropdown
3. Click **Start Logging** to begin
4. Switch to a different area or click **Stop** to end logging
5. View your time history and export as CSV

### Logging Tasks/Services

1. Go to **T/S Log** from the dashboard
2. Enter task name, description, and category
3. Click **Start** to begin
4. Click **Stop** when complete
5. View task history with duration details

### Viewing Timecard

1. Go to **Timecard** from the dashboard
2. Select date range to view
3. See aggregated hours by area and charge code
4. View visualizations of time allocation

### Management Console

1. Go to **Management** from the dashboard
2. Manage **Charge Codes** - Add, edit, or delete charge codes
3. Manage **Areas** - Add, edit, or delete work areas
4. Associate charge codes with areas

## Project Structure

```
├── APP.py                      # Flask application entry point
├── config.py                   # Configuration management
├── models.py                   # Database models and operations
├── auth.py                     # Authentication routes
├── area_logger.py              # Area logging routes
├── timecard.py                 # Timecard summary routes
├── ts_log.py                   # Task/Service logging routes
├── management.py               # Management console routes
├── utils.py                    # Utility functions
├── requirements.txt            # Python dependencies
├── templates/                  # HTML templates
│   ├── base.html              # Base template with navigation
│   ├── login.html             # Login/signup page
│   ├── dashboard.html         # Main dashboard
│   ├── area_logger.html       # Area logging interface
│   ├── ts_log.html            # Task/Service logging interface
│   ├── timecard.html          # Timecard summary view
│   ├── charge_codes.html      # Charge codes management
│   ├── areas.html             # Areas management
│   ├── 404.html, 500.html, 403.html  # Error pages
│   └── ...
├── static/                     # Static assets
│   ├── app.js                 # JavaScript functionality
│   ├── style.css              # Application styling
│   └── ...
├── helpers/                    # Helper modules
│   └── exporter.py            # Export utilities
├── instance/                   # Instance folder (database, local config)
│   └── timecard.db            # SQLite database (created on first run)
├── logs/                       # Application logs
│   └── app.log               # Main application log
└── .gitignore                 # Git ignore rules
```

## API Routes

### Authentication
- `GET/POST /login` - User login
- `POST /signup` - User registration (via login page)
- `GET /logout` - User logout

### Dashboard
- `GET /` - Main dashboard

### Area Logging
- `GET/POST /area-logger/` - Area logging interface
- `GET /area-logger/export` - Export area logs as CSV

### Task/Service Logging
- `GET/POST /ts-log/` - Task/Service logging interface

### Timecard
- `GET /timecard/` - Timecard summary

### Management
- `GET /management/charge-codes` - List charge codes
- `GET/POST /management/charge-codes/create` - Create charge code
- `GET/POST /management/charge-codes/<id>/edit` - Edit charge code
- `POST /management/charge-codes/<id>/delete` - Delete charge code
- `GET /management/areas` - List areas
- `GET/POST /management/areas/create` - Create area
- `GET/POST /management/areas/<id>/edit` - Edit area
- `POST /management/areas/<id>/delete` - Delete area

## Database Schema

### Users
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);
```

### Charge Codes
```sql
CREATE TABLE charge_code (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Areas
```sql
CREATE TABLE area (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    charge_code_id INTEGER,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(charge_code_id) REFERENCES charge_code(id)
);
```

### Time Logs
```sql
CREATE TABLE time_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    area_id INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES user(id),
    FOREIGN KEY(area_id) REFERENCES area(id)
);
```

### Task/Service Logs
```sql
CREATE TABLE ts_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    task_name TEXT NOT NULL,
    description TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES user(id)
);
```

## Configuration

Environment variables can be set to customize the application:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `development` | Flask environment (development/production) |
| `SECRET_KEY` | `dev-secret-change-me-in-production` | Flask secret key (change in production) |
| `DEBUG` | `False` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `SESSION_COOKIE_SECURE` | `False` | HTTPS-only cookies (set True in production) |

## Logging

Application logs are stored in the `logs/` directory:
- **Log File**: `logs/app.log`
- **Console Output**: Also printed to terminal when running

Log levels:
- `DEBUG`: Detailed development information
- `INFO`: General informational messages
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for serious problems

## Security Features

- ✅ Password hashing with Werkzeug
- ✅ Session management with HTTP-only cookies
- ✅ CSRF protection via Flask
- ✅ Security headers (X-Content-Type-Options, X-Frame-Options, etc.)
- ✅ SQL injection prevention via parameterized queries
- ✅ Input validation and sanitization
- ✅ Login required decorator for protected routes

## Development

### Code Style

The codebase follows PEP 8 and includes:
- Type hints for better code clarity
- Comprehensive docstrings for modules and functions
- Consistent error handling
- Proper logging throughout

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=. tests/
```

## Troubleshooting

### Application won't start
1. Ensure Python 3.8+ is installed
2. Activate virtual environment
3. Install all dependencies: `pip install -r requirements.txt`
4. Check logs in `logs/app.log`

### Database errors
1. The database is automatically created on first run
2. Delete `instance/timecard.db` to start fresh
3. Check file permissions on `instance/` folder

### Port already in use
Change the port in APP.py:
```python
app.run(debug=True, port=5001)
```

### Login issues
1. Ensure cookies are enabled in your browser
2. Check that `SECRET_KEY` is set appropriately
3. Try clearing browser cookies and cache

## Contributing

Contributions are welcome! Please follow these guidelines:
1. Fork the repository
2. Create a feature branch
3. Make your changes with proper documentation
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Authors

- **Zachary Mangiafesto** - Initial development
- **James Homan** - Contributions

## Support

For issues or questions, please create an issue on GitHub or contact the development team.

## Version History

- **v1.0.0** (2026-04-03) - Professional release with comprehensive documentation and error handling

---

**Last Updated**: 2026-04-03  
**Status**: Actively Maintained ✓
