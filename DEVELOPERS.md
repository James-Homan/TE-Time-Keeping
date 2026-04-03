# Development Guidelines for TE Timekeeping

## Code Quality Standards

### Python Style

- Follow PEP 8
- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Include docstrings for all modules, classes, and functions

### Type Hints

All new code should include type hints:

```python
def function_name(param1: str, param2: int) -> bool:
    """Brief description of function.
    
    Args:
        param1: Description of param1.
        param2: Description of param2.
        
    Returns:
        Description of return value.
    """
    pass
```

### Docstring Format

Use Google-style docstrings:

```python
def example_function(param1: str) -> str:
    """Brief one-line description.
    
    Extended description of what the function does, including
    any important details about behavior or side effects.
    
    Args:
        param1: Description of parameter.
        
    Returns:
        Description of return value.
        
    Raises:
        ValueError: When something goes wrong.
    """
```

## Setting Up Development Environment

### 1. Clone Repository
```bash
git clone https://github.com/zmanja42-ai/Time-Card-Management.git
cd Time-Card-Management
```

### 2. Create Virtual Environment
```bash
python -m venv .dev-venv
source .dev-venv/bin/activate  # or .dev-venv\Scripts\activate on Windows
```

### 3. Install Development Dependencies
```bash
pip install -r requirements.txt
pip install pytest pytest-cov black flake8 mypy
```

### 4. Pre-commit Setup (Optional)
Create a `.git/hooks/pre-commit` file:
```bash
#!/bin/bash
black --check .
flake8 .
mypy .
```

## Testing

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_basic.py

# Run specific test
pytest tests/test_basic.py::TestAuth::test_login_page_loads
```

### Writing Tests

1. Create test files in `tests/` directory
2. Name files `test_*.py`
3. Use descriptive test names: `test_<functionality>_<case>`
4. Use fixtures for setup/teardown
5. Aim for >80% code coverage

Example:
```python
def test_user_creation_with_valid_data():
    """Test that valid user data creates a user."""
    user = create_user("testuser", "password123")
    assert user is not None
    assert user.username == "testuser"
```

## Git Workflow

### Branches

- `main` - Production code
- `develop` - Development integration branch
- `feature/<name>` - Feature branches
- `bugfix/<name>` - Bug fix branches

### Commit Messages

Follow conventional commits:
```
type(scope): subject

body

footer
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(auth): add password strength validation

- Add minimum 8 character requirement
- Check for uppercase and numbers
- Display helpful error messages

Fixes #123
```

### Pull Request Process

1. Create feature branch from `develop`
2. Make changes with descriptive commits
3. Write or update tests
4. Update documentation
5. Create pull request with clear description
6. Address code review comments
7. Merge when approved

## Code Review Checklist

- [ ] Code follows PEP 8 style guide
- [ ] Type hints are present
- [ ] Docstrings are complete and accurate
- [ ] Error handling is appropriate
- [ ] Logging is included where needed
- [ ] No hardcoded values (use config)
- [ ] Tests are included and passing
- [ ] No security vulnerabilities
- [ ] Database operations use parameterized queries
- [ ] Comments explain "why", not "what"

## Common Development Tasks

### Add a New Route

1. Create the view function in appropriate module
2. Add route decorator with proper HTTP methods
3. Include docstring explaining functionality
4. Add login_required decorator if needed
5. Add appropriate error handling and logging
6. Create tests in `tests/` directory
7. Update documentation

### Add a New Database Model

1. Update schema in `models.py` `init_db()` function
2. Add helper functions for CRUD operations
3. Include comprehensive docstrings
4. Add type hints
5. Create migration if needed
6. Add tests

### Update Configuration

1. Add to `config.py` class
2. Document in README.md
3. Add default environment variable handling
4. Update development guidelines

## Debugging

### Enable Debug Mode
```python
app = create_app()
app.run(debug=True)
```

### View Logs
```bash
tail -f logs/app.log
```

### Database Browser
Use a SQLite browser to inspect database:
- Windows/macOS/Linux: https://sqlitebrowser.org/
- View `instance/timecard.db`

### Flask Shell
```bash
flask shell
from models import *
db = get_db()
# Query away!
```

## Performance Considerations

1. **Database Queries**: Avoid N+1 queries, use JOIN operations
2. **Caching**: Use appropriate caching for static data
3. **Session Management**: Keep session data minimal
4. **Logging**: Don't log sensitive information

## Security Best Practices

1. **Input Validation**: Always validate user input
2. **SQL Injection**: Use parameterized queries (always!)
3. **Password Handling**: Never log or display passwords
4. **CSRF Protection**: Flask handles by default
5. **XSS Prevention**: Use Jinja2 escaping (automatic in templates)
6. **Authentication**: Use decorators for protected routes
7. **Secrets**: Keep in environment variables, never in code

## Documentation

- Update README.md for user-facing changes
- Update DEVELOPERS.md for development process changes
- Include docstrings in all new code
- Add examples for new features
- Keep API documentation current

## Release Process

1. Update version in `__init__.py`
2. Update CHANGELOG.md
3. Create release notes
4. Tag release in git
5. Deploy to production

---

**Questions?** Contact the development team or open an issue on GitHub.
