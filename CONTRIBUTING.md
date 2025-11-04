# Contributing to Axon

Thank you for your interest in contributing to Axon! This document provides guidelines and instructions for development.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip and virtualenv

### Setting Up Your Environment

1. **Clone the repository**
   ```bash
   git clone https://github.com/axonml/axon.git
   cd axon
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   .\venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install the package in editable mode with dev dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify installation**
   ```bash
   python -c "import axon; print(axon.__version__)"
   pytest --version
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=axon --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py

# Run specific test
pytest tests/unit/test_models.py::TestMemoryEntry::test_entry_creation_minimal
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code with Black
black src/ tests/

# Lint with Ruff
ruff check src/ tests/

# Type check with mypy
mypy src/axon
```

### Pre-commit Checklist

Before committing code, ensure:

- [ ] All tests pass: `pytest`
- [ ] Code is formatted: `black src/ tests/`
- [ ] No linting errors: `ruff check src/ tests/`
- [ ] Type checking passes: `mypy src/axon`
- [ ] Test coverage is maintained: `pytest --cov=axon`
- [ ] Documentation is updated if needed

## Code Style Guidelines

### Python Style

- Follow PEP 8 (enforced by Black and Ruff)
- Maximum line length: 100 characters
- Use type hints for all function signatures
- Write docstrings for all public APIs (Google style)

### Documentation

- All public modules, classes, and functions must have docstrings
- Use Google-style docstrings
- Include examples in docstrings where helpful
- Keep README.md up to date

### Testing

- Write unit tests for all new functionality
- Aim for >90% code coverage
- Use descriptive test names: `test_<what>_<condition>_<expected>`
- Use pytest fixtures for shared test data

## Sprint-Based Development

Axon follows a sprint-based development process defined in `AGENTS.md`. Each sprint follows this workflow:

1. **Planning** - Review sprint plan and get approval
2. **Implementation** - Write code according to spec
3. **Verification** - Review code quality and adherence
4. **Testing** - Validate functionality
5. **Review** - Document outcomes and prepare next steps

See `AGENTS.md` for detailed process documentation.

## Commit Message Guidelines

Use conventional commits format:

```
type(scope): subject

body (optional)

footer (optional)
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Example:
```
feat(models): add MemoryEntry provenance tracking

Implement add_provenance() method to track actions on memory entries
for audit trail and explainability.

Closes #42
```

## Project Structure

```
axon/
├── src/axon/          # Main package
│   ├── models/        # Data models
│   ├── adapters/      # Storage adapters
│   ├── core/          # Core logic
│   └── utils/         # Utilities
├── tests/             # Test suite
│   ├── unit/          # Unit tests
│   └── integration/   # Integration tests
├── examples/          # Usage examples
└── docs/              # Documentation
```

## Questions or Issues?

- Check existing issues on GitHub
- Open a new issue with detailed description
- Join our community discussions

## License

By contributing to Axon, you agree that your contributions will be licensed under the MIT License.
