# Contributing to OpenClaw Cron Scheduler

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip or poetry for dependency management
- git for version control

### Setting Up Development Environment

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/Fourier7754/openclaw-cron-scheduler.git
   cd openclaw-cron-scheduler
   ```

3. Install in editable mode with dev dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Run tests to verify your setup:
   ```bash
   pytest
   ```

## Development Workflow

### Making Changes

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```

2. Make your changes following the coding style guidelines

3. Run tests and linting:
   ```bash
   pytest
   black --check openclaw_cron_scheduler tests
   mypy openclaw_cron_scheduler
   ```

4. Commit your changes with a clear message:
   ```bash
   git commit -m "feat: add XYZ feature"
   ```

5. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Create a pull request on GitHub

### Coding Style

- Follow PEP 8 guidelines
- Use Black for code formatting (line length: 100)
- Add type hints for new functions
- Write docstrings for public APIs
- Keep functions focused and small

### Testing

- Write unit tests for new functionality
- Maintain test coverage above 80%
- Use pytest for testing
- Mock external dependencies

### Commit Message Format

We follow the Conventional Commits specification:

- `feat:` - A new feature
- `fix:` - A bug fix
- `docs:` - Documentation only changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add support for configuration file overrides
fix: resolve race condition in queue management
docs: update README with new usage examples
```

## Pull Request Guidelines

### Before Submitting

- [ ] Code follows project style guidelines
- [ ] Tests pass locally
- [ ] Documentation is updated
- [ ] Commit messages follow the format
- [ ] PR description clearly explains the changes

### PR Review Process

1. Automated checks must pass (CI/CD)
2. At least one maintainer approval is required
3. Address review comments promptly
4. Keep the PR focused and small if possible

### What Gets Accepted

- Bug fixes with tests
- Well-documented new features
- Performance improvements
- Documentation improvements
- Test coverage improvements

## Reporting Issues

When reporting issues, please include:

- Python and package version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Logs or error messages

## Questions?

Feel free to open an issue with the "question" label or start a discussion.

Thank you for contributing!
