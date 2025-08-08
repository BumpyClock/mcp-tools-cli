# Testing Guide for MCP Manager

This document describes the comprehensive testing suite implemented for the MCP Manager TUI application as part of Phase 5.4: Integration & Cross-Platform Testing.

## Overview

The MCP Manager includes a comprehensive testing framework designed to ensure production readiness across different environments and user scenarios. The testing suite covers:

- **End-to-end workflow testing**
- **Comprehensive keyboard shortcut validation**
- **Error handling and recovery scenarios**
- **Performance testing with large datasets**
- **Cross-platform terminal compatibility**

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Global pytest configuration and fixtures
├── test_*.py                   # Unit tests
├── integration/                # Integration tests
│   ├── __init__.py
│   ├── test_workflows.py       # End-to-end workflow tests
│   ├── test_keyboard_shortcuts.py  # Keyboard shortcut tests
│   └── test_error_scenarios.py # Error handling tests
├── performance/                # Performance tests
│   ├── __init__.py
│   └── test_large_datasets.py  # Large dataset performance tests
├── compatibility/              # Cross-platform compatibility tests
│   ├── __init__.py
│   ├── test_terminals.py       # Terminal compatibility tests
│   └── test_platforms.py       # Platform-specific tests
└── fixtures/                   # Test data and utilities
    ├── __init__.py
    └── test_data_generators.py # Test data factories
```

## Test Categories

### 1. Unit Tests
- **Location**: `tests/test_*.py`
- **Purpose**: Test individual components in isolation
- **Run with**: `make test-unit` or `pytest tests/ -m unit`

### 2. Integration Tests
- **Location**: `tests/integration/`
- **Purpose**: Test complete user workflows and component interactions

#### 2.1 Workflow Tests (`test_workflows.py`)
Tests complete user journeys from start to finish:

- **Server Lifecycle**: Add → Configure → Deploy → Monitor → Remove
- **Deployment Workflow**: Select servers → Choose targets → Deploy → Verify → Rollback
- **Health Monitoring**: Start monitoring → Detect issues → Show alerts → Resolve
- **View Switching**: Registry view → Project view → Server view → Back to registry
- **Batch Operations**: Multi-server selection and bulk operations
- **Error Recovery**: Handle failures and maintain application stability

#### 2.2 Keyboard Shortcut Tests (`test_keyboard_shortcuts.py`)
Comprehensive testing of all 15+ keyboard shortcuts:

- **Primary Actions**: A(dd), E(dit), D(eploy), R(efresh), H(ealth), Q(uit)
- **Navigation**: Tab, Shift+Tab, Arrow keys, Enter, Escape
- **Context-Sensitive**: Different behavior based on focused pane
- **Multi-Selection**: Space bar for multi-select mode
- **Conflict Resolution**: Ensure no shortcut conflicts
- **Accessibility**: All functionality accessible via keyboard

#### 2.3 Error Scenario Tests (`test_error_scenarios.py`)
Tests error handling and recovery:

- **Configuration Errors**: Invalid configs, missing files, corrupted data
- **Network Errors**: Connection failures, timeouts, intermittent issues
- **Resource Exhaustion**: Memory limits, disk space, file handles
- **Permission Errors**: Access denied, read-only filesystem
- **Data Corruption**: Malformed JSON, encoding errors
- **Concurrency Issues**: Race conditions, deadlock prevention
- **Recovery Mechanisms**: Automatic retry, rollback, state consistency

### 3. Performance Tests
- **Location**: `tests/performance/`
- **Purpose**: Ensure performance meets requirements under load

#### 3.1 Large Dataset Tests (`test_large_datasets.py`)
Performance testing with scalable datasets:

- **Startup Time**: TUI initialization with 50+, 100+, 200+ servers
- **Navigation Performance**: Responsive UI with large datasets
- **Memory Usage**: Monitor memory consumption and detect leaks
- **Deployment Matrix**: Large server/project matrix performance
- **Bulk Operations**: Multi-server deployment performance
- **UI Responsiveness**: Maintain responsiveness during background operations

**Performance Thresholds**:
- Startup: < 2s (100 servers), < 5s (200+ servers)
- Operations: < 5s for typical operations
- Memory: < 100MB for basic datasets
- Navigation: < 0.05s per operation

### 4. Compatibility Tests
- **Location**: `tests/compatibility/`
- **Purpose**: Ensure cross-platform and terminal compatibility

#### 4.1 Terminal Compatibility (`test_terminals.py`)
Tests across different terminal environments:

- **Windows Terminals**: Windows Terminal, cmd.exe, PowerShell, ConEmu
- **Color Schemes**: 256-color, 16-color, monochrome, high contrast
- **Font Rendering**: Unicode, emoji, box drawing characters
- **Screen Sizes**: Small (80x24), large (200x60), dynamic resize
- **Accessibility**: Screen reader compatibility, keyboard-only navigation

#### 4.2 Platform Compatibility (`test_platforms.py`)
Tests platform-specific behaviors:

- **Windows**: Path handling (backslashes), executable detection (.exe)
- **macOS**: Unix paths, Homebrew integration, Terminal.app
- **Linux**: Package manager paths, distribution compatibility
- **Cross-Platform**: Path normalization, environment variables

## Test Data and Fixtures

### Test Data Generators (`tests/fixtures/test_data_generators.py`)
Provides factories for creating realistic test data:

- **ServerConfigFactory**: Generate server configurations
- **ProjectConfigFactory**: Generate project configurations
- **DeploymentStateFactory**: Generate deployment states
- **TestScenarioFactory**: Generate complete test environments

#### Test Environments Available:
- **Empty**: Clean slate for testing fresh start
- **Small**: 5 servers, 3 projects - basic workflow testing
- **Medium**: 20 servers, 8 projects - comprehensive testing
- **Large**: 100+ servers, 15+ projects - performance testing
- **Problematic**: Servers with various configuration issues

## Running Tests

### Quick Test Commands

```bash
# Fast unit tests (recommended for development)
make test-fast

# All unit tests
make test-unit

# Integration tests
make test-integration

# Performance tests (may take several minutes)
make test-performance

# Compatibility tests
make test-compatibility

# Smoke tests (quick validation)
make test-smoke

# Comprehensive test suite
make test-comprehensive

# Tests with coverage
make test-coverage
```

### Platform-Specific Test Runners

#### Windows (PowerShell)
```powershell
# Quick tests
.\scripts\test_quick.ps1

# With coverage
.\scripts\test_quick.ps1 -Coverage

# Parallel execution
.\scripts\test_quick.ps1 -Parallel

# Specific test type
.\scripts\test_quick.ps1 -TestType integration
```

#### Unix-like Systems (Linux/macOS)
```bash
# Quick tests
./scripts/test_quick.sh

# With coverage
./scripts/test_quick.sh --coverage

# Parallel execution
./scripts/test_quick.sh --parallel

# Specific test type
./scripts/test_quick.sh --type integration
```

### Advanced Test Execution

#### Python Test Runner
```bash
# Comprehensive test suite
python scripts/run_tests.py comprehensive

# Parallel execution
python scripts/run_tests.py all --parallel

# With timeout
python scripts/run_tests.py integration --timeout 60
```

#### Direct pytest Commands
```bash
# Run specific test file
pytest tests/integration/test_workflows.py -v

# Run tests matching pattern
pytest tests/ -k "test_keyboard" -v

# Run tests with markers
pytest tests/ -m "not slow" -v

# Run tests with coverage
pytest tests/ --cov=src/mcp_manager --cov-report=html

# Run tests in parallel
pytest tests/ -n auto
```

## Continuous Integration

### GitHub Actions Workflow
The project includes a comprehensive CI/CD pipeline (`.github/workflows/test.yml`) that runs:

1. **Smoke Tests**: Quick validation on every commit
2. **Unit Tests**: Across Python 3.8-3.12 on Ubuntu, Windows, macOS
3. **Integration Tests**: With coverage reporting
4. **Performance Tests**: Performance regression detection
5. **Compatibility Tests**: Cross-platform validation
6. **Code Quality**: Linting, formatting, type checking
7. **Security Checks**: Vulnerability scanning

### Test Execution Matrix
- **Platforms**: Ubuntu, Windows, macOS
- **Python Versions**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Test Types**: Unit, Integration, Performance, Compatibility
- **Coverage**: Minimum 80% code coverage required

## Test Configuration

### pytest Configuration (`pytest.ini`)
```ini
[tool:pytest]
testpaths = tests
addopts = --verbose --cov=src/mcp_manager --cov-report=term-missing --cov-fail-under=80
markers =
    integration: Integration tests
    performance: Performance tests  
    compatibility: Compatibility tests
    slow: Slow running tests
    smoke: Essential smoke tests
```

### Global Fixtures (`tests/conftest.py`)
Provides common fixtures for all tests:
- Test environments (empty, small, medium, large, problematic)
- Mock components (registry, deployment manager, health monitor)
- Performance monitoring
- Memory leak detection
- Platform-specific skipping

## Test Development Guidelines

### Writing New Tests

1. **Use Appropriate Markers**:
```python
@pytest.mark.integration
async def test_my_integration():
    pass

@pytest.mark.performance
@pytest.mark.slow
async def test_my_performance():
    pass
```

2. **Use Fixtures for Common Setup**:
```python
async def test_with_small_environment(small_test_environment):
    servers = small_test_environment["servers"]
    # Test implementation
```

3. **Follow TDD Principles**:
   - Write failing test first
   - Implement minimal code to pass
   - Refactor while keeping tests green

4. **Mock External Dependencies**:
```python
@patch('mcp_manager.tui_app.MCPServerRegistry')
async def test_with_mock_registry(mock_registry):
    # Test implementation
```

### Performance Test Guidelines

1. **Use Performance Monitor**:
```python
async def test_performance(performance_monitor):
    performance_monitor.start_monitoring()
    # Test operations
    metrics = performance_monitor.stop_monitoring()
    assert metrics["duration"] < threshold
```

2. **Set Realistic Thresholds**:
   - Consider different hardware capabilities
   - Allow for CI environment overhead
   - Use parametrized tests for different dataset sizes

### Compatibility Test Guidelines

1. **Mock Platform Differences**:
```python
with patch('platform.system', return_value="Windows"):
    # Test Windows-specific behavior
```

2. **Test Environment Variables**:
```python
with patch.dict(os.environ, {"TERM": "xterm-256color"}):
    # Test with specific terminal capabilities
```

## Test Maintenance

### Regular Tasks
- Update test data generators when adding new server types
- Review performance thresholds periodically
- Update compatibility tests for new terminal versions
- Maintain CI pipeline dependencies

### Debugging Tests
```bash
# Run tests with detailed output
pytest tests/ -vv --tb=long

# Run specific test with PDB
pytest tests/test_specific.py::test_function --pdb

# Run tests without capturing output
pytest tests/ -s

# Run tests with memory monitoring
pytest tests/ --memmon
```

## Coverage Requirements

### Minimum Coverage Targets
- **Overall**: 80% minimum (enforced by CI)
- **Core functionality**: 90%+ recommended
- **Integration workflows**: 100% of major user journeys
- **Error scenarios**: All error conditions covered

### Coverage Reports
```bash
# Generate HTML coverage report
make coverage-html

# Serve coverage report in browser
make serve-coverage

# View coverage in terminal
pytest tests/ --cov=src/mcp_manager --cov-report=term-missing
```

## Troubleshooting

### Common Issues

1. **Tests Timeout**: Increase timeout or optimize test performance
2. **Memory Leaks**: Use memory monitor fixture to detect issues
3. **Platform Failures**: Check platform-specific mocking
4. **Flaky Tests**: Add proper waiting/retry mechanisms

### Test Environment Issues
```bash
# Reset test environment
make clean

# Reinstall test dependencies
make install-test

# Check pytest installation
python -m pytest --version
```

This comprehensive testing framework ensures that the MCP Manager TUI is production-ready, reliable, and works consistently across all target environments and user scenarios.