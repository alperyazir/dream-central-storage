# Test Strategy and Standards

## Testing Philosophy
- **Approach**: Test-After development for the MVP.
- **Coverage Goals**: Aim for a minimum of 80% code coverage.
- **Test Pyramid**: A strong base of Unit Tests, with a focused set of Integration Tests.

## Test Types and Organization
- **Unit Tests**: Use Pytest and unittest.mock. Located in `app/tests/unit/`.
- **Integration Tests**: Use Pytest and Testcontainers to spin up a temporary PostgreSQL container for realistic testing. Located in `app/tests/integration/`.

## Test Data Management
- **Strategy**: Use Pytest fixtures to create and manage test data.

---
