# Contributing to Meridian

Thank you for your interest in contributing to Meridian! This document provides guidelines and steps for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and constructive environment for all contributors.

## How to Contribute

### Reporting Bugs

1. Check the [Issues](https://github.com/CartesianXR7/meridian/issues) to ensure the bug hasn't been reported
2. If not found, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected and actual behavior
   - System information and environment details

### Suggesting Enhancements

1. Create an issue labeled "enhancement"
2. Include:
   - Clear use case
   - Proposed implementation details (if any)
   - Why this enhancement would benefit the project

### Pull Requests

1. Fork the repository
2. Create a new branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes
4. Follow the coding standards:
   - Use consistent indentation (4 spaces)
   - Follow PEP 8 guidelines
   - Add docstrings and comments
   - Include type hints where applicable
5. Add tests if relevant
6. Update documentation if needed
7. Commit with clear messages:
   ```bash
   git commit -m "feat: add new feature" -m "Detailed description"
   ```
8. Push to your fork
9. Create a Pull Request

## Development Setup

1. Fork and clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install development dependencies:
   ```bash
   pip install black flake8 pytest
   ```

## Testing

- Run tests before submitting PRs:
  ```bash
  pytest
  ```
- Ensure code passes linting:
  ```bash
  black .
  flake8
  ```

## Documentation

- Update documentation for any changed functionality
- Include docstrings for new functions/classes
- Update README.md if needed

## Questions?

Feel free to create an issue labeled "question" or contact the maintainer directly.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
