# Terminal Progress Indicators: Best Practices & Library Review

## Overview

This document reviews best practices and open-source libraries for implementing progress indicators in terminal-based CLI applications, specifically for the OME (Open Matching Engine) FastAPI/CLI system where async operations can take 5+ minutes to complete.

## Current System Context

- **Framework**: Click-based CLI with async command support
- **Operations**: Async operations that can take 5+ minutes
- **Existing Dependencies**: `tqdm` is already in `requirements.txt`
- **Output**: Terminal-based, supports JSON/table/text formats
 
## Best Practices

### 1. Non-Blocking Updates
- Progress indicators must not block the async event loop
- Updates should be lightweight and infrequent enough to avoid performance impact
- Use async-compatible libraries or proper async integration patterns

### 2. Clear User Feedback
- Display current operation/stage name
- Show percentage completion when total is known
- Display elapsed time and estimated time remaining (ETA)
- For indeterminate operations, use spinners or animated indicators
- Provide context about what's happening (e.g., "Downloading file 3/10")

### 3. Graceful Degradation
- Disable progress indicators when output is redirected (pipes, files)
- Respect `--verbose` and `--json` flags (may want to suppress progress in JSON mode)
- Handle terminal size changes gracefully
- Work well in CI/CD environments

### 4. Performance Considerations
- Minimal overhead (progress updates should be <1% of total time)
- Batch updates when possible (don't update on every iteration)
- Use efficient rendering (avoid full screen redraws)

### 5. Integration with Existing Patterns
- Work with Click's async command decorators
- Respect existing `--verbose` flag behavior
- Integrate with `CLIContext` and `SmartCommand` patterns
- Support both HTTP API calls and direct service fallback modes

## Library Comparison

### 1. tqdm ⭐ (Already Installed)

**Pros:**
- ✅ Already in `requirements.txt`
- ✅ Very popular and well-maintained
- ✅ Excellent async support via `tqdm.asyncio`
- ✅ Lightweight and performant
- ✅ Works well with iterables and manual updates
- ✅ Automatic terminal detection and redirection handling
- ✅ Extensive customization options

**Cons:**
- ⚠️ Less visually appealing than `rich`
- ⚠️ Basic styling compared to modern alternatives

**Async Support:**
```python
from tqdm.asyncio import tqdm

async for item in tqdm.as_completed(coroutines, desc="Processing"):
    result = await item
```

**Best For:**
- Quick integration (already installed)
- Simple progress bars for loops/iterables
- When minimal dependencies are preferred

**Example Usage:**
```python
from tqdm import tqdm
import asyncio

# Simple progress bar
for i in tqdm(range(100), desc="Processing"):
    await some_async_operation()

# Manual updates
pbar = tqdm(total=100, desc="Building package")
for i in range(100):
    await process_item(i)
    pbar.update(1)
pbar.close()
```

---

### 2. rich.progress ⭐⭐⭐ (Recommended)

**Pros:**
- ✅ Beautiful, modern terminal output with colors
- ✅ Excellent async support
- ✅ Multiple progress bars (track multiple tasks)
- ✅ Rich formatting (spinners, columns, tables)
- ✅ Built-in support for indeterminate tasks
- ✅ Great Click integration examples
- ✅ Excellent documentation
- ✅ Handles terminal resizing gracefully

**Cons:**
- ⚠️ Additional dependency (not currently installed)
- ⚠️ Slightly more complex API than tqdm

**Async Support:**
```python
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

async with Progress() as progress:
    task = progress.add_task("[green]Processing...", total=100)
    while not progress.finished:
        await do_work()
        progress.update(task, advance=1)
```

**Best For:**
- Modern, visually appealing progress indicators
- Multiple concurrent operations
- When you want rich terminal formatting
- Long-running operations with multiple stages

**Example Usage:**
```python
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    TimeElapsedColumn(),
    TimeRemainingColumn(),
) as progress:
    task = progress.add_task("Building package...", total=100)
    for i in range(100):
        await process_item(i)
        progress.update(task, advance=1)
```

---

### 3. alive-progress

**Pros:**
- ✅ Highly animated and visually engaging
- ✅ Great for long-running operations
- ✅ Shows throughput statistics
- ✅ Multiple bar styles and themes

**Cons:**
- ⚠️ Additional dependency
- ⚠️ Less common, smaller community
- ⚠️ Async support requires careful integration
- ⚠️ May be too "busy" for some users

**Best For:**
- When you want maximum visual appeal
- Long-running operations where users need engagement
- When throughput metrics are important

---

### 4. progressbar2

**Pros:**
- ✅ Traditional, familiar look
- ✅ Good customization options
- ✅ Stable and mature

**Cons:**
- ⚠️ Less modern appearance
- ⚠️ Async support is limited
- ⚠️ Not as actively maintained as tqdm/rich

**Best For:**
- Legacy compatibility
- Simple, traditional progress bars

---

## Recommendations for OME CLI

### Primary Recommendation: **rich.progress**

**Rationale:**
1. **Modern UX**: Beautiful, colored output that enhances user experience
2. **Multiple Tasks**: Can track multiple concurrent operations (e.g., "Downloading files", "Validating manifest", "Building package")
3. **Indeterminate Support**: Great for operations where total progress is unknown
4. **Click Integration**: Works seamlessly with Click's async commands
5. **Future-Proof**: Rich ecosystem for other terminal enhancements

**Implementation Strategy:**
- Add `rich` to `requirements.txt`
- Create a progress utility module in `src/cli/progress.py`
- Integrate with `CLIContext` for consistent progress display
- Support both determinate (known total) and indeterminate (spinner) modes

### Secondary Option: **tqdm** (Quick Start)

**Rationale:**
1. **Already Installed**: No new dependencies
2. **Quick Integration**: Can be added immediately
3. **Proven**: Battle-tested in many projects
4. **Async Support**: Good async integration via `tqdm.asyncio`

**Implementation Strategy:**
- Use existing `tqdm` installation
- Create progress wrapper utilities
- Integrate with existing command patterns

## Implementation Patterns

### Pattern 1: Context Manager for Long Operations

```python
# Using rich
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

async def long_operation():
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        task = progress.add_task("Processing...", total=100)
        # ... operation logic ...
        progress.update(task, advance=1)
```

### Pattern 2: Multi-Stage Progress

```python
# Track multiple stages of a long operation
with Progress() as progress:
    download_task = progress.add_task("Downloading files...", total=10)
    validate_task = progress.add_task("Validating...", total=None)  # Indeterminate
    build_task = progress.add_task("Building package...", total=100)
    
    # Stage 1: Download
    for i in range(10):
        await download_file(i)
        progress.update(download_task, advance=1)
    
    # Stage 2: Validate (indeterminate)
    progress.update(validate_task, description="Validating manifest...")
    await validate_manifest()
    progress.update(validate_task, completed=True)
    
    # Stage 3: Build
    for i in range(100):
        await build_step(i)
        progress.update(build_task, advance=1)
```

### Pattern 3: Integration with CLIContext

```python
# In src/cli/base.py or new src/cli/progress.py
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

class CLIContext:
    def __init__(self, config: CLIConfig):
        # ... existing code ...
        self._progress = None
    
    def get_progress(self) -> Optional[Progress]:
        """Get progress indicator, respecting verbose and output format flags"""
        if self.output_format == 'json':
            return None  # Don't show progress in JSON mode
        if not self.verbose and self._progress is None:
            # Create progress only when needed
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            )
            self._progress.start()
        return self._progress
```

### Pattern 4: Async Operation Wrapper

```python
from contextlib import asynccontextmanager
from rich.progress import Progress

@asynccontextmanager
async def progress_context(description: str, total: Optional[int] = None):
    """Context manager for progress tracking"""
    with Progress() as progress:
        task = progress.add_task(description, total=total)
        yield lambda advance=1: progress.update(task, advance=advance)
        progress.update(task, completed=True)

# Usage
async def build_package():
    async with progress_context("Building package...", total=100) as update:
        for i in range(100):
            await process_step(i)
            update(1)
```

## Integration Points in OME CLI

### Commands That Would Benefit from Progress Indicators

1. **Package Building** (`ome package build`)
   - Downloading files (known total)
   - Validating files (indeterminate)
   - Organizing structure (known total)

2. **LLM Generation** (`ome llm generate-okh`)
   - Analyzing repository (indeterminate)
   - Generating manifest (indeterminate)
   - Reviewing output (indeterminate)

3. **Matching Operations** (`ome match`)
   - Searching capabilities (indeterminate)
   - Matching requirements (known total)
   - Ranking results (known total)

4. **Package Push/Pull** (`ome package push/pull`)
   - Uploading/downloading files (known total)
   - Verifying integrity (indeterminate)

5. **OKH Generation from URL** (`ome okh generate-from-url`)
   - Cloning repository (indeterminate)
   - Extracting project data (indeterminate)
   - Generating manifest (indeterminate)

## Integration with Existing Metrics System

The OME codebase already includes a comprehensive metrics tracking system (`src/core/errors/metrics.py`) that tracks:
- **PerformanceMetrics**: Operation durations, throughput, resource usage
- **ErrorMetrics**: Error rates and patterns
- **LLMMetrics**: LLM usage, costs, and performance
- **MetricsTracker**: Unified interface for HTTP and LLM request tracking

### Integration Opportunities

#### 1. Smart ETA Estimation (Optional Enhancement)

Use historical metrics to provide better ETA estimates:

```python
from src.core.errors.metrics import get_performance_metrics

class SmartProgressTracker:
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.metrics = get_performance_metrics()
        self.start_time = datetime.now()
    
    def get_estimated_total_time(self) -> Optional[float]:
        """Get estimated total time based on historical data"""
        stats = self.metrics.get_performance_summary()
        operation_stats = stats.get("operation_stats", {}).get(self.operation_name)
        
        if operation_stats:
            # Use p95 duration as estimate (conservative)
            return operation_stats.get("p95_duration_ms", 0) / 1000
        return None
    
    def get_eta(self, progress: float) -> Optional[timedelta]:
        """Calculate ETA based on current progress and historical data"""
        if progress <= 0:
            return None
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        estimated_total = self.get_estimated_total_time()
        
        if estimated_total:
            # Use historical estimate
            remaining = (estimated_total * (1 - progress))
        else:
            # Fallback to linear projection
            remaining = (elapsed / progress) * (1 - progress)
        
        return timedelta(seconds=remaining)
```

#### 2. Progress Milestone Reporting (Optional)

Report progress milestones to metrics system for analysis:

```python
class MetricsAwareProgress:
    def __init__(self, operation_name: str, component: str = "cli"):
        self.operation_name = operation_name
        self.component = component
        self.metrics = get_performance_metrics()
        self.stage_start_time = None
        self.current_stage = None
    
    def start_stage(self, stage_name: str):
        """Start tracking a new stage"""
        if self.current_stage and self.stage_start_time:
            # Record previous stage duration
            duration_ms = (datetime.now() - self.stage_start_time).total_seconds() * 1000
            self.metrics.record_operation(
                operation=f"{self.operation_name}:{self.current_stage}",
                duration_ms=duration_ms,
                component=self.component,
                success=True
            )
        
        self.current_stage = stage_name
        self.stage_start_time = datetime.now()
    
    def finish(self):
        """Finish tracking and record final metrics"""
        if self.current_stage and self.stage_start_time:
            duration_ms = (datetime.now() - self.stage_start_time).total_seconds() * 1000
            self.metrics.record_operation(
                operation=f"{self.operation_name}:{self.current_stage}",
                duration_ms=duration_ms,
                component=self.component,
                success=True
            )
```

#### 3. Integration Pattern (Optional, Non-Blocking)

Make metrics integration optional and non-blocking:

```python
from typing import Optional
from src.core.errors.metrics import get_performance_metrics

class ProgressTracker:
    def __init__(self, operation_name: str, use_metrics: bool = True):
        self.operation_name = operation_name
        self.use_metrics = use_metrics
        self._metrics = None
        
        if use_metrics:
            try:
                self._metrics = get_performance_metrics()
            except Exception:
                # Gracefully degrade if metrics unavailable
                self.use_metrics = False
    
    def get_eta_estimate(self, progress: float) -> Optional[timedelta]:
        """Get ETA estimate, using metrics if available"""
        if not self.use_metrics or not self._metrics:
            return None  # Fallback to default ETA calculation
        
        try:
            # Use metrics for smart ETA
            stats = self._metrics.get_performance_summary()
            # ... ETA calculation using historical data
        except Exception:
            # Don't fail if metrics query fails
            return None
```

### Integration Benefits

1. **Better UX**: More accurate ETA estimates based on historical data
2. **Analytics**: Track which operations/stages take longest
3. **Optimization**: Identify bottlenecks through stage-level metrics
4. **Consistency**: Unified tracking across API and CLI operations

### Integration Considerations

- **Optional**: Progress indicators should work without metrics system
- **Non-Blocking**: Metrics queries should not slow down progress updates
- **Graceful Degradation**: Handle cases where metrics system is unavailable
- **Performance**: Cache metrics queries to avoid overhead on every update

### Recommended Approach

1. **Phase 1**: Implement basic progress indicators without metrics integration
2. **Phase 2**: Add optional metrics integration for ETA estimation
3. **Phase 3**: Add progress milestone reporting for analytics

This allows progress indicators to be useful immediately while enabling future enhancements.

## Next Steps

1. **Choose Library**: Decide between `rich` (recommended) or `tqdm` (quick start)
2. **Create Progress Utility Module**: `src/cli/progress.py` with reusable progress utilities
3. **Integrate with CLIContext**: Add progress support to existing context system
4. **Implement in One Command**: Start with one long-running command as a proof of concept
5. **Optional Metrics Integration**: Add metrics-aware ETA estimation (Phase 2)
6. **Iterate**: Add progress indicators to other commands incrementally

## References

- [tqdm Documentation](https://tqdm.github.io/)
- [tqdm.asyncio](https://tqdm.github.io/docs/contrib.asyncio/)
- [rich.progress Documentation](https://rich.readthedocs.io/en/stable/progress.html)
- [Click with rich](https://click.palletsprojects.com/en/8.1.x/advanced/#command-output)
- [alive-progress GitHub](https://github.com/rsalmei/alive-progress)
- OME Metrics System: `src/core/errors/metrics.py`

