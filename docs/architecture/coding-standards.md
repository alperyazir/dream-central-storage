# Coding Standards

## Core Standards
- **Language**: Python 3.11.x
- **Style & Linting**: We will use Black for code formatting and Ruff for linting.
- **Test Organization**: Tests will reside in `app/tests/`, with filenames following `test_*.py`.
- **Naming Conventions**: Adherence to the standard Python PEP 8 style guide.

## Critical Rules
- Use the Data Access Layer: All database operations MUST go through functions in `app/crud/`.
- Type Hint Everything: All function signatures and variables MUST include Python type hints.
- Use Pydantic for API Schemas: All API request/response bodies MUST be defined using Pydantic models in `app/schemas/`.
- Centralized Configuration: Settings MUST be accessed through the config object from `app/core/config.py`.

---
