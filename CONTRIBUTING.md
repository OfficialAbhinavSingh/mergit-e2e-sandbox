# CONTRIBUTING.md - Fix for Issue #19
# Contributor Documentation for mergit-e2e-sandbox

# Contributing to mergit-e2e-sandbox

Welcome! Thank you for your interest in contributing to the mergit-e2e-sandbox project.

## About This Project

**mergit-e2e-sandbox** is a throwaway repository used for end-to-end testing of [Mergit](https://mergit.dev)'s GitHub tools and automation capabilities. This sandbox environment is used to exercise and validate:

- Pull Request operations (open, read, review, merge)
- Diff reading and analysis
- Code review workflows
- Merge operations with guard functionality
- Comments and labels
- Issue and PR closing

**Important:** Everything in this repository is disposable and may be reset or modified at any time for testing purposes.

## Project Structure

```
mergit-e2e-sandbox/
├── README.md              # Project overview
├── CONTRIBUTING.md        # This file
├── calc.py               # Simple calculator module for testing
├── .github/
│   └── workflows/        # CI/CD workflows for testing
└── tests/                # Test files (if present)
```

## The Calculator Module

The `calc.py` file contains a simple calculator with the following functions:

- `average(numbers)` - Returns the average of a list of numbers
- `total(numbers)` - Returns the sum of a list of numbers
- `largest(numbers)` - Returns the largest number in a list

This module serves as a simple codebase for testing Mergit's PR and review capabilities.

## Getting Started

### Prerequisites

- Python 3.7 or higher
- Git

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/OfficialAbhinavSingh/mergit-e2e-sandbox.git
   cd mergit-e2e-sandbox
   ```

2. (Optional) Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

## Running Tests

To test the calculator module:

```bash
python calc.py
```

This will run the example calculations defined in the `__main__` block.

## CI/CD Workflows

This repository includes GitHub Actions workflows that are intentionally configured to test Mergit's merge guard functionality. Some workflows may deliberately fail to validate that Mergit correctly handles failed checks.

## Contributing Guidelines

Since this is a sandbox repository for testing, contributions are primarily for:

1. **Improving test coverage** - Add new test cases or edge cases
2. **Enhancing the calculator** - Add new functions or improve existing ones
3. **Documentation** - Help improve documentation and examples
4. **CI/CD improvements** - Enhance or add workflows for better testing

### Making Changes

1. Create a new branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them:
   ```bash
   git commit -m "Description of your changes"
   ```

3. Push to your fork and create a Pull Request:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Your PR will be reviewed and tested by Mergit's automation tools.

## Code Style

- Follow PEP 8 guidelines for Python code
- Add docstrings to functions
- Keep functions simple and focused
- Add comments for complex logic

## Testing Your Changes

Before submitting a PR, ensure your changes work correctly:

```bash
python calc.py
```

## Questions or Issues?

If you have questions about contributing or encounter issues:

1. Check the existing issues and PRs
2. Open a new issue with a clear description
3. Reference this CONTRIBUTING.md file if relevant

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to mergit-e2e-sandbox! Your contributions help improve Mergit's testing and automation capabilities.