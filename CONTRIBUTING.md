# Contributing to HCP Terraform No-Code Portal

Thank you for your interest in contributing to this project! This guide will help you set up your development environment and understand the contribution workflow.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- pip and venv
- Git

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/gitrgoliveira/tfc-no-code-portal.git
   cd tfc-no-code-portal
   ```

2. **Install dependencies and setup development tools**:
   ```bash
   make install-dev
   ```

   This will:
   - Create a virtual environment
   - Install all dependencies (including development tools)
   - Setup pre-commit hooks

3. **Activate the virtual environment**:
   ```bash
   source venv/bin/activate
   ```

## Development Workflow

### Running the Application

```bash
make run
```

Access the application at `http://localhost:8501`

### Code Quality Checks

We use several tools to maintain code quality:

#### Linting

```bash
make lint          # Check for code issues
make lint-fix      # Auto-fix issues where possible
```

#### Formatting

```bash
make format-check  # Check formatting without changes
make format        # Format all code
```

#### Type Checking

```bash
make type-check    # Run mypy type checker
```

#### Run All Checks

```bash
make verify        # Runs lint, type-check, and tests
```

### Testing

```bash
make test          # Run tests with coverage report
make test-quick    # Run tests without coverage (faster)
```

View HTML coverage report: `open htmlcov/index.html`

### Pre-commit Hooks

Pre-commit hooks run automatically before each commit. To run them manually:

```bash
make pre-commit
```

If hooks fail, fix the issues and try committing again.

## Code Style Guidelines

### General Principles

- **Clarity over cleverness**: Write code that's easy to understand
- **Type hints**: Add type hints to all new functions
- **Documentation**: Add docstrings to public functions
- **Tests**: Add tests for new features

### Python Style

- **Line length**: 120 characters maximum
- **Imports**: Group stdlib → third-party → local, alphabetically
- **String formatting**: Use f-strings
- **Naming**:
  - Functions/variables:snake_case
  - Classes: PascalCase
  - Constants: UPPER_SNAKE_CASE

### Type Hints

Always add type hints to new functions:

```python
def process_workspace(name: str, config: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Process workspace configuration.
    
    Args:
        name: Workspace name
        config: Configuration dictionary
        
    Returns:
        Processed configuration or None if validation fails
    """
    ...
```

### Error Handling

Use specific exception types:

```python
try:
    data = json.load(file)
except (json.JSONDecodeError, FileNotFoundError) as e:
    logging.warning(f"Failed to load config: {e}")
    return None
```

Provide user-friendly error messages in the UI:

```python
except ConnectionError:
    st.error("❌ Cannot connect to HCP Terraform. Check your network connection.")
```

## Project Structure

```
.
├── constants.py          # Application constants and enums
├── portal.py            # Main Streamlit application
├── no_code.py           # Payload generator
├── validation.py        # Input validation utilities
├── utils.py             # Shared utility functions
├── tests/               # Test suite
│   ├── conftest.py      # Pytest fixtures
│   ├── test_auth.py     # Authentication tests
│   ├── test_validation.py  # Validation tests
│   ├── test_payload.py  # Payload generation tests
│   └── test_utils.py    # Utility function tests
├── pyproject.toml       # Tool configuration
├── requirements.in      # Direct dependencies
├── requirements.txt     # Pinned dependencies (auto-generated)
└── Makefile            # Development commands
```

## Adding New Features

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write tests first** (TDD approach):
   - Add tests to `tests/test_*.py`
   - Run tests: `make test`

3. **Implement the feature**:
   - Follow code style guidelines
   - Add type hints
   - Add docstrings

4. **Validate your changes**:
   ```bash
   make verify  # Runs linting, type-checking, and tests
   ```

5. **Commit and push**:
   ```bash
   git add .
   git commit -m "Add feature: description"
   git push origin feature/your-feature-name
   ```

6. **Create a pull request**:
   - Describe your changes
   - Reference any related issues
   - Ensure CI checks pass

## Testing Guidelines

### Writing Tests

- Use pytest fixtures from `tests/conftest.py`
- Mock external dependencies (API calls, file I/O)
- Test edge cases and error conditions
- Aim for >80% code coverage on new code

### Test Organization

```python
class TestFeatureName:
    """Tests for feature description."""
    
    def test_basic_functionality(self):
        """Test the happy path."""
        ...
    
    def test_error_handling(self):
        """Test error conditions."""
        ...
    
    def test_edge_cases(self):
        """Test boundary conditions."""
        ...
```

### Running Specific Tests

```bash
pytest tests/test_auth.py              # Run one file
pytest tests/test_auth.py::TestClass  # Run one class
pytest tests/test_auth.py::test_name  # Run one test
pytest -k "pattern"                   # Run tests matching pattern
```

## Common Tasks

### Adding a New Dependency

1. Add to `requirements.in`:
   ```
   new-package>=1.0.0
   ```

2. Update requirements.txt:
   ```bash
   make requirements
   ```

### Adding a New Constant

Add to `constants.py`:

```python
NEW_CONSTANT = "value"
```

Import in other files:

```python
from constants import NEW_CONSTANT
```

### Adding a New Validation Function

1. Add function to `validation.py`
2. Add tests to `tests/test_validation.py`
3. Use in portal.py

## Getting Help

- **Issues**: Check [existing issues](https://github.com/gitrgoliveira/tfc-no-code-portal/issues)
- **Discussions**: Start a [discussion](https://github.com/gitrgoliveira/tfc-no-code-portal/discussions)
- **Documentation**: See [README.md](README.md) and [AGENTS.md](AGENTS.md)

## Code Review Process

All contributions require code review:

1Maintain existing code style
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure CI checks pass
5. Respond to review feedback

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
