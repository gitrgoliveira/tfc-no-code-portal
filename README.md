# No-Code Deployment Application with HCP Terraform

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)

## Overview

This is a no-code deployment application that leverages HCP Terraform to automate the provisioning and management of infrastructure resources. With this application, you can easily deploy and manage your infrastructure without writing any code.

The application provides a user-friendly Streamlit interface that wraps the Terraform Cloud API (`terrasnek` library) to enable infrastructure deployment without direct HCP Terraform UI interaction.

## Features

- **No-Code Deployment**: Deploy infrastructure resources through an intuitive web interface
- **HCP Terraform Integration**: Automatic token discovery from multiple sources (environment variables, credentials file)
- **Dynamic Form Generation**: Variable inputs auto-generated based on module requirements
- **Workspace Management**: View and manage existing workspaces by project
- **Input Validation**: Workspace names and variable values validated before deployment
- **Multi-Project Support**: Deploy to different projects within your organization
- **Settings Persistence**: URL parameters preserve configuration across page refreshes

## Prerequisites

Before using this application, ensure you have:

### HCP Terraform Requirements
- **Organization**: An HCP Terraform organization
- **Token**: API token with appropriate permissions
- **No-code modules**: At least one registry module marked as no-code

### Local Requirements
- **Python**: 3.11 or higher
- **pip**: Package installer for Python
- **Git**: Version control

## Installation

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/gitrgoliveira/tfc-no-code-portal.git
   cd tfc-no-code-portal
   ```

2. **Run the application**:
   ```bash
   make run
   ```
   Or alternatively:
   ```bash
   ./run_portal.sh
   ```

3. **Access the application**:
   The application will automatically open in your browser at `http://localhost:8501`

### Development Installation

For development with testing and linting tools:

```bash
make install-dev
```

This installs all dependencies and sets up pre-commit hooks.

## Usage

### Authentication

The application automatically discovers your HCP Terraform token from multiple sources (in priority order):

1. **Environment variable**: `TF_TOKEN_{hostname}` (e.g., `TF_TOKEN_app_terraform_io`)
2. **Credentials file**: `~/.terraform.d/credentials.tfrc.json`
3. **Legacy environment variable**: `TFC_TOKEN`

Alternatively, you can manually enter your token in the UI.

### Basic Workflow

1. **Configure Settings** (Sidebar):
   - Enter HCP Terraform URL (defaults to https://app.terraform.io)
   - Token will be auto-discovered or enter manually
   - Select your organization
   - Click "Apply configuration"

2. **Deploy Infrastructure**:
   - Choose the "Direct Module Deployment" tab
   - Select target project
   - Click a module to deploy
   - Enter workspace name and required variables
   - Click "Deploy"

3. **View Workspaces**:
   - Current infrastructure displayed by project
   - Click workspace links to open in HCP Terraform

## Development

### Available Commands

```bash
make help            # Show all available commands
make run             # Run the application
make test            # Run tests with coverage
make lint            # Run code linter
make format          # Format code
make type-check      # Run type checker
make verify          # Run all quality checks
make clean           # Clean up generated files
```

### Running Tests

```bash
make test            # Full test suite with coverage
make test-quick      # Quick tests without coverage
```

View coverage report: `open htmlcov/index.html`

### Code Quality

The project uses:
- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checker
- **pytest**: Testing framework
- **pre-commit**: Git hooks for quality checks

Run all quality checks:
```bash
make verify
```

### Project Structure

```
.
├── constants.py          # Application constants
├── portal.py            # Main Streamlit application
├── no_code.py           # Payload generator for deployments
├── validation.py        # Input validation utilities
├── utils.py             # Shared utility functions
├── tests/               # Test suite
├── pyproject.toml       # Tool configuration
├── requirements.in      # Direct dependencies
├── requirements.txt     # Pinned dependencies
└── Makefile            # Development commands
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development guidelines.

## Troubleshooting

### Token Not Found

```bash
# Set token environment variable
export TF_TOKEN_app_terraform_io="your-token-here"

# OR use Terraform CLI
terraform login
```

### Connection Errors

- Verify HCP Terraform URL is correct
- Check network connectivity
- Ensure token has required permissions

### Module Not Appearing

- Ensure module is marked as "no-code" in registry
- Verify you have access to the module's organization
- Refresh the module list with "Clear cache and refresh"

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup instructions
- Code style guidelines
- Testing requirements
- Pull request process

## Documentation

- **[AGENTS.md](AGENTS.md)**: Detailed architectural documentation
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: Development and contribution guidelines
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)**: AI agent instructions

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/gitrgoliveira/tfc-no-code-portal/issues)
- **Discussions**: [GitHub Discussions](https://github.com/gitrgoliveira/tfc-no-code-portal/discussions)

