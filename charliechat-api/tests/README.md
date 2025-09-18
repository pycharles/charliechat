# Charlie Chat API Test Suite

This directory contains the comprehensive test suite for the Charlie Chat API application.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (one per source file)
│   ├── __init__.py
│   ├── test_ai_service.py
│   ├── test_chat_service_session_state.py
│   └── test_prompt_engineering.py
├── integration/             # Integration tests
│   └── __init__.py
└── fixtures/                # Test data and fixtures
```

## Test Organization

### Unit Tests (`tests/unit/`)
- **One test file per source file**: `test_<module_name>.py`
- **Test class per class**: `Test<ClassName>`
- **Test methods**: `test_<functionality>`
- **Fast execution**: Mock external dependencies
- **Isolated**: Each test is independent

### Integration Tests (`tests/integration/`)
- **End-to-end testing**: Full application flow
- **Real dependencies**: Use actual services where appropriate
- **Slower execution**: May involve network calls or database operations
- **Environment setup**: May require specific test environment

## Running Tests

### Using the Test Runner Script
```bash
# Run all unit tests
./run_tests.py unit

# Run integration tests
./run_tests.py integration

# Run all tests
./run_tests.py all

# Run specific session state tests
./run_tests.py session-state

# Run with coverage
./run_tests.py coverage
```

### Using pytest directly
```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_chat_service_session_state.py

# Run specific test method
pytest tests/unit/test_chat_service_session_state.py::TestChatServiceSessionState::test_first_request_creates_conversation_history
```

## Test Categories

### Unit Tests
- **`test_ai_service.py`**: Tests for AI service functionality
  - Prompt building with/without context
  - Knowledge base retrieval
  - Response length calculation
  - Bedrock integration (mocked)
  - Error handling

- **`test_chat_service_session_state.py`**: Tests for session state preservation
  - Conversation history creation
  - Session state persistence across requests
  - JSON serialization/deserialization
  - Conversation history limits
  - Error handling for malformed data

- **`test_prompt_engineering.py`**: Tests for prompt engineering
  - KB query parameter selection
  - Context summarization
  - Response length calculation
  - Question type detection

### Integration Tests (Future)
- **`test_api_endpoints.py`**: Full API endpoint testing
- **`test_htmx_integration.py`**: Frontend-backend integration
- **`test_lambda_deployment.py`**: AWS Lambda deployment testing

## Test Fixtures

### Shared Fixtures (`conftest.py`)
- **`test_settings`**: Test configuration with environment variables
- **`mock_bedrock_client`**: Mock AWS Bedrock client
- **`mock_bedrock_agent_client`**: Mock Bedrock Agent client
- **`sample_session_state`**: Sample session state for testing
- **`sample_conversation_history`**: Sample conversation history

### Test-Specific Fixtures
Each test file can define its own fixtures for specific test data.

## Test Data

### Session State Examples
```python
{
    "conversation_history": [
        {
            "question": "tell me about skills",
            "answer": "Charlie has extensive experience in software engineering..."
        }
    ],
    "current_voice_style": "normal",
    "last_question": "tell me about skills",
    "last_answer": "Charlie has extensive experience..."
}
```

## Best Practices

### Writing Tests
1. **Arrange-Act-Assert**: Structure tests clearly
2. **Descriptive names**: Test names should describe what they test
3. **One assertion per test**: Focus on one behavior per test
4. **Mock external dependencies**: Keep tests fast and isolated
5. **Test edge cases**: Include error conditions and boundary cases

### Test Organization
1. **Mirror source structure**: Easy to find corresponding tests
2. **Group related tests**: Use test classes for related functionality
3. **Use fixtures**: Share common test data and setup
4. **Mark slow tests**: Use `@pytest.mark.slow` for integration tests

### Coverage Goals
- **Unit tests**: 90%+ code coverage
- **Critical paths**: 100% coverage for session state and AI service
- **Error handling**: Test all error conditions
- **Edge cases**: Test boundary conditions and malformed input

## Continuous Integration

Tests should be run:
- **Before commits**: Pre-commit hooks
- **On pull requests**: Automated CI/CD pipeline
- **Before deployments**: Full test suite validation
- **Regularly**: Scheduled test runs for regression detection

## Debugging Tests

### Running Individual Tests
```bash
# Run specific test with verbose output
pytest -v tests/unit/test_chat_service_session_state.py::TestChatServiceSessionState::test_first_request_creates_conversation_history

# Run with print statements visible
pytest -s tests/unit/test_chat_service_session_state.py

# Run with debugging
pytest --pdb tests/unit/test_chat_service_session_state.py
```

### Test Output
- **Verbose mode**: Shows individual test names and results
- **Coverage report**: Shows which lines are covered by tests
- **HTML coverage**: Generate `htmlcov/index.html` for detailed coverage

## Adding New Tests

### For New Features
1. **Write tests first**: Follow TDD principles
2. **Test the interface**: Focus on public methods and behavior
3. **Mock dependencies**: Keep tests isolated and fast
4. **Test error cases**: Include failure scenarios

### For Bug Fixes
1. **Reproduce the bug**: Write a failing test that demonstrates the issue
2. **Fix the code**: Implement the fix
3. **Verify the fix**: Ensure the test now passes
4. **Add regression test**: Prevent the bug from returning

## Test Environment

### Local Development
- **Python 3.11+**: Required for async/await support
- **Virtual environment**: Isolate dependencies
- **Environment variables**: Use test-specific values
- **Mock services**: Avoid external API calls during testing

### CI/CD Pipeline
- **Automated setup**: Install dependencies and run tests
- **Parallel execution**: Run tests in parallel for speed
- **Coverage reporting**: Track coverage trends over time
- **Test artifacts**: Save test reports and coverage data
