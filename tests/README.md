# Videogen Test Suite

This directory contains a comprehensive, organized test suite for the videogen pipeline with mocked APIs to avoid expensive external calls.

## 📁 Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_pipeline.py     # Pipeline unit tests
│   ├── test_worker.py       # Worker unit tests
│   └── test_methods.py      # Method unit tests
├── integration/             # Integration tests for full pipeline
│   └── test_full_pipeline.py
├── fixtures/                # Test fixtures and utilities
│   └── test_fixtures.py
├── mocks/                   # Mock API responses
│   └── api_mocks.py
├── json_data/               # Test JSON data files
│   └── openai_demo2.json
├── run_all_tests.py         # Main test runner
└── README.md               # This file
```

## 🚀 Running Tests

### Run All Tests
```bash
# Run the complete test suite
python tests/run_all_tests.py

# Or run the legacy test file (redirects to new structure)
python test_pipeline_comprehensive.py
```

### Run Specific Test Categories
```bash
# Run only unit tests
python -m unittest discover tests/unit -v

# Run only integration tests
python -m unittest discover tests/integration -v

# Run specific test file
python tests/unit/test_pipeline.py
```

## 🎭 Mocked APIs

All expensive external API calls are mocked:

- **LLM APIs**: OpenAI, Anthropic, etc. (for decision making and prompt generation)
- **SiliconFlow Video API**: Video generation and status checking
- **SiliconFlow TTS API**: Text-to-speech generation
- **Playwright**: Browser automation for React rendering
- **FFmpeg**: Video processing and resizing
- **HTTP Requests**: All external API calls

## 📊 Test Coverage

### Unit Tests (25 tests)
- **Pipeline Tests**: Decision making, error handling, task skipping
- **Worker Tests**: Video submission, status checking, downloading, CSV operations
- **Method Tests**: Text video, audio generation, React rendering

### Integration Tests (8 tests)
- **Full Pipeline**: End-to-end pipeline execution
- **Audio Generation**: TTS integration
- **Video Processing**: Complete video workflow
- **Error Handling**: Pipeline error scenarios
- **Folder Structure**: New organized video folder structure

## 🛠️ Test Utilities

### TestEnvironment
Manages test project creation and cleanup:
```python
with TestEnvironment() as env:
    project = env.create_test_project("my_test")
    # Test code here
    # Automatic cleanup
```

### TestDataFactory
Creates test data and fixtures:
```python
# Create test project JSON
TestDataFactory.create_openai_demo2_json(project.json_path)

# Create test CSV data
TestDataFactory.create_csv_test_data(csv_path)
```

### MockAPIs
Centralized mock responses:
```python
# Get mock LLM response
response = MockAPIs.get_llm_response("decider")

# Get mock SiliconFlow response
submit_resp = MockAPIs.get_siliconflow_submit_response()
```

## 🎯 Key Features

1. **No API Costs**: All expensive calls are mocked
2. **Fast Execution**: Tests run in seconds, not minutes
3. **Comprehensive Coverage**: Tests entire pipeline flow
4. **Organized Structure**: Easy to maintain and extend
5. **Realistic Data**: Uses actual project JSON structure
6. **Video Folder Structure**: Tests new organized folder structure

## 📈 Benefits

- **Cost Effective**: No external API charges during testing
- **Reliable**: No dependency on external services
- **Fast**: Quick feedback during development
- **Maintainable**: Well-organized, modular structure
- **Extensible**: Easy to add new tests and mocks

## 🔧 Adding New Tests

### Unit Tests
Create new test files in `tests/unit/` following the pattern:
```python
class TestNewComponent(unittest.TestCase):
    def setUp(self):
        self.test_env = TestEnvironment()
        self.project = self.test_env.create_test_project()
    
    def tearDown(self):
        self.test_env.cleanup()
    
    def test_new_functionality(self):
        # Test implementation
        pass
```

### Integration Tests
Add to `tests/integration/test_full_pipeline.py` or create new files.

### Mock APIs
Add new mock responses to `tests/mocks/api_mocks.py`.

## 🎉 Success Criteria

All tests should pass with:
- ✅ Unit Tests: 25/25 passed
- ✅ Integration Tests: 8/8 passed
- 🎯 Overall Result: ALL TESTS PASSED

This ensures the videogen pipeline is working correctly with mocked APIs before using real (expensive) external services.
