# ABOUTME: Quick test runner PowerShell script for Windows development workflow
# ABOUTME: Provides fast test execution with common test configurations

param(
    [string]$TestType = "fast",
    [switch]$Parallel,
    [switch]$Coverage,
    [switch]$Verbose,
    [int]$Timeout = 30
)

# Colors for output
$Green = "Green"
$Red = "Red"  
$Yellow = "Yellow"
$Cyan = "Cyan"

Write-Host "🚀 MCP Manager Test Runner" -ForegroundColor $Cyan
Write-Host "=========================" -ForegroundColor $Cyan

# Check if we're in the right directory
if (-not (Test-Path "pyproject.toml")) {
    Write-Host "❌ Not in project root directory" -ForegroundColor $Red
    exit 1
}

# Build pytest command
$command = @("python", "-m", "pytest")

switch ($TestType.ToLower()) {
    "unit" {
        $command += @("tests/", "-m", "unit")
    }
    "integration" { 
        $command += @("tests/integration/")
    }
    "performance" {
        $command += @("tests/performance/")
    }
    "compatibility" {
        $command += @("tests/compatibility/")
    }
    "smoke" {
        $command += @("-m", "smoke")
    }
    "fast" {
        $command += @("tests/", "-m", "not slow and not performance")
    }
    "all" {
        $command += @("tests/")
    }
    default {
        Write-Host "❌ Unknown test type: $TestType" -ForegroundColor $Red
        Write-Host "Available types: unit, integration, performance, compatibility, smoke, fast, all"
        exit 1
    }
}

# Add common options
$command += @("--tb=short", "-v")

# Add optional flags
if ($Parallel) {
    $workers = [Math]::Min([Environment]::ProcessorCount, 4)
    $command += @("-n", $workers)
    Write-Host "🔄 Running tests in parallel ($workers workers)" -ForegroundColor $Yellow
}

if ($Coverage) {
    $command += @("--cov=src/mcp_manager", "--cov-report=term-missing", "--cov-report=html:htmlcov")
    Write-Host "📊 Coverage reporting enabled" -ForegroundColor $Yellow
}

if ($Verbose) {
    $command += @("-vv")
}

$command += @("--timeout", $Timeout)

# Show command being run
Write-Host "Command: $($command -join ' ')" -ForegroundColor $Cyan
Write-Host ""

# Run tests
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

try {
    $result = & $command[0] $command[1..($command.Length-1)]
    $exitCode = $LASTEXITCODE
}
catch {
    Write-Host "💥 Error running tests: $_" -ForegroundColor $Red
    exit 1
}
finally {
    $stopwatch.Stop()
}

# Show results
Write-Host ""
Write-Host "=========================" -ForegroundColor $Cyan
if ($exitCode -eq 0) {
    Write-Host "✅ Tests PASSED in $($stopwatch.Elapsed.TotalSeconds.ToString('F2'))s" -ForegroundColor $Green
} else {
    Write-Host "❌ Tests FAILED in $($stopwatch.Elapsed.TotalSeconds.ToString('F2'))s" -ForegroundColor $Red
}

# Show coverage report location if generated
if ($Coverage -and (Test-Path "htmlcov/index.html")) {
    Write-Host "📊 Coverage report: htmlcov/index.html" -ForegroundColor $Yellow
}

exit $exitCode