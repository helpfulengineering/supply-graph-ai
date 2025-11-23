# Progress Indicators Implementation Specification

## Overview

This specification defines the implementation of terminal progress indicators for the OME CLI using `rich.progress`. The solution will provide visual feedback for long-running async operations while maintaining compatibility with existing CLI patterns and design principles.

**Library Choice**: `rich.progress` ([Documentation](https://rich.readthedocs.io/en/stable/reference/progress.html#))

**Implementation Approach**: Phase 1 - CLI-Level Progress (incremental, non-invasive)

---

## Goals and Requirements

### Primary Goals
1. Provide visual progress feedback for operations taking 5+ minutes
2. Integrate seamlessly with existing CLI architecture
3. Support both HTTP API and direct service call paths
4. Respect existing CLI flags (`--verbose`, `--json`, `--table`)
5. Maintain async compatibility and performance

### Non-Goals (Phase 1)
- Service-level progress callbacks (Phase 2)
- Metrics integration for smart ETAs (Phase 3)
- Streaming HTTP responses for progress (future enhancement)

---

## Architecture

### Component Structure

```
src/cli/
├── base.py                    # CLIContext (enhanced with progress support)
├── progress.py                # NEW: Progress utility module
│   ├── ProgressManager        # Main progress management class
│   ├── ProgressStage          # Stage tracking and context managers
│   └── progress_helpers       # Helper functions and utilities
└── [command modules]          # Commands using progress utilities
```

### Integration Points

1. **CLIContext Enhancement**: Add progress management to existing context
2. **Progress Utility Module**: Reusable progress tracking utilities
3. **Command Integration**: Wrap service calls with progress indicators
4. **SmartCommand Pattern**: Progress works with existing fallback mechanism

---

## API Design

### 1. ProgressManager Class

**Location**: `src/cli/progress.py`

**Purpose**: Central manager for progress indicators, integrated with CLIContext

```python
class ProgressManager:
    """
    Manages progress indicators for CLI commands.
    
    Handles creation, lifecycle, and cleanup of progress displays.
    Integrates with CLIContext to respect output format and verbose flags.
    """
    
    def __init__(
        self,
        cli_ctx: CLIContext,
        enabled: bool = True,
        transient: bool = False,
        refresh_per_second: float = 10.0
    ):
        """
        Initialize progress manager.
        
        Args:
            cli_ctx: CLI context for configuration
            enabled: Whether progress is enabled (respects --json, --verbose)
            transient: Clear progress on completion
            refresh_per_second: Refresh rate for progress updates
        """
    
    def __enter__(self) -> 'ProgressManager':
        """Context manager entry"""
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with cleanup"""
    
    def add_stage(
        self,
        description: str,
        total: Optional[float] = None,
        **kwargs
    ) -> 'ProgressStage':
        """
        Add a new progress stage.
        
        Args:
            description: Stage description (supports rich markup)
            total: Total units (None for indeterminate)
            **kwargs: Additional task parameters
        
        Returns:
            ProgressStage for managing this stage
        """
    
    def update_stage(
        self,
        stage: 'ProgressStage',
        advance: float = 1.0,
        description: Optional[str] = None,
        **kwargs
    ) -> None:
        """Update a progress stage"""
    
    def complete_stage(self, stage: 'ProgressStage') -> None:
        """Mark a stage as complete"""
    
    def is_enabled(self) -> bool:
        """Check if progress is enabled"""
```

### 2. ProgressStage Class

**Purpose**: Represents a single progress stage/task

```python
class ProgressStage:
    """
    Represents a single progress stage.
    
    Can be used as a context manager for automatic stage lifecycle.
    """
    
    def __init__(
        self,
        manager: ProgressManager,
        task_id: int,
        description: str,
        total: Optional[float] = None
    ):
        """Initialize progress stage"""
    
    def __enter__(self) -> 'ProgressStage':
        """Context manager entry"""
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - auto-complete stage"""
    
    def update(
        self,
        advance: float = 1.0,
        description: Optional[str] = None,
        **kwargs
    ) -> None:
        """Update progress for this stage"""
    
    def complete(self) -> None:
        """Mark stage as complete"""
    
    @property
    def task_id(self) -> int:
        """Get task ID"""
```

### 3. Helper Functions

```python
def should_show_progress(cli_ctx: CLIContext) -> bool:
    """
    Determine if progress should be shown.
    
    Rules:
    - Disabled if output_format == 'json'
    - Enabled if verbose is True (shows detailed progress)
    - Enabled by default for long operations
    """
    return cli_ctx.output_format != 'json'

def create_progress_manager(
    cli_ctx: CLIContext,
    **kwargs
) -> ProgressManager:
    """Factory function to create progress manager with defaults"""

@asynccontextmanager
async def progress_stage(
    manager: ProgressManager,
    description: str,
    total: Optional[float] = None,
    **kwargs
) -> AsyncIterator[ProgressStage]:
    """Async context manager for progress stages"""
```

---

## Rich.Progress Configuration

### Default Column Layout

Based on [rich.progress documentation](https://rich.readthedocs.io/en/stable/reference/progress.html#), we'll use:

```python
from rich.progress import (
    Progress,
    SpinnerColumn,      # Animated spinner for indeterminate tasks
    TextColumn,         # Task description
    BarColumn,          # Visual progress bar
    TaskProgressColumn, # Percentage and progress text
    TimeElapsedColumn,  # Elapsed time
    TimeRemainingColumn # ETA (when total is known)
)

# For determinate tasks (known total)
DETERMINATE_COLUMNS = [
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    TimeElapsedColumn(),
    TimeRemainingColumn(),
]

# For indeterminate tasks (unknown total)
INDETERMINATE_COLUMNS = [
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(pulse_style="bar.pulse"),
    TimeElapsedColumn(),
]
```

### Progress Configuration

```python
PROGRESS_CONFIG = {
    "auto_refresh": True,
    "refresh_per_second": 10.0,  # Balance between smoothness and performance
    "speed_estimate_period": 30.0,  # For ETA calculation
    "transient": False,  # Keep progress visible after completion
    "console": None,  # Use default console (respects terminal capabilities)
    "disable": False,  # Controlled by should_show_progress()
}
```

---

## Integration with CLIContext

### Enhanced CLIContext

**Location**: `src/cli/base.py`

**Changes**:
```python
class CLIContext:
    def __init__(self, config: CLIConfig):
        # ... existing code ...
        self._progress_manager: Optional[ProgressManager] = None
    
    def get_progress_manager(self) -> Optional[ProgressManager]:
        """
        Get or create progress manager.
        
        Returns None if progress should be disabled.
        """
        if self._progress_manager is None:
            if should_show_progress(self):
                self._progress_manager = create_progress_manager(self)
        return self._progress_manager
    
    def start_progress(self) -> ProgressManager:
        """Start progress tracking (context manager)"""
        manager = self.get_progress_manager()
        if manager:
            return manager.__enter__()
        return None
    
    def stop_progress(self) -> None:
        """Stop progress tracking"""
        if self._progress_manager:
            self._progress_manager.__exit__(None, None, None)
            self._progress_manager = None
```

---

## Command Integration Patterns

### Pattern 1: Single-Stage Operation

**Use Case**: Simple operations with one progress stage

```python
async def simple_command(ctx, ...):
    cli_ctx = ctx.obj
    
    with cli_ctx.get_progress_manager() as progress:
        stage = progress.add_stage("Processing...", total=100)
        
        for i in range(100):
            await do_work(i)
            progress.update_stage(stage, advance=1)
```

### Pattern 2: Multi-Stage Operation

**Use Case**: Operations with multiple distinct stages

```python
async def multi_stage_command(ctx, ...):
    cli_ctx = ctx.obj
    
    with cli_ctx.get_progress_manager() as progress:
        # Stage 1: Downloading
        download_stage = progress.add_stage(
            "Downloading files...",
            total=file_count
        )
        for file in files:
            await download_file(file)
            progress.update_stage(download_stage, advance=1)
        progress.complete_stage(download_stage)
        
        # Stage 2: Validating (indeterminate)
        validate_stage = progress.add_stage("Validating files...")
        await validate_files()
        progress.complete_stage(validate_stage)
        
        # Stage 3: Building
        build_stage = progress.add_stage(
            "Building package...",
            total=build_steps
        )
        for step in build_steps:
            await build_step(step)
            progress.update_stage(build_stage, advance=1)
```

### Pattern 3: Stage Context Manager

**Use Case**: Automatic stage lifecycle management

```python
async def command_with_stages(ctx, ...):
    cli_ctx = ctx.obj
    
    with cli_ctx.get_progress_manager() as progress:
        # Stage automatically completes on exit
        with progress.add_stage("Downloading...", total=10) as stage:
            for i in range(10):
                await download(i)
                stage.update(advance=1)
        
        # Next stage
        with progress.add_stage("Validating...") as stage:
            await validate()
```

### Pattern 4: HTTP + Fallback Pattern

**Use Case**: Commands using SmartCommand.execute_with_fallback()

```python
async def command_with_fallback(ctx, ...):
    cli_ctx = ctx.obj
    
    with cli_ctx.get_progress_manager() as progress:
        # Show progress for connection attempt
        conn_stage = progress.add_stage("Connecting to server...")
        
        async def http_operation():
            progress.update_stage(conn_stage, description="Sending request...")
            result = await cli_ctx.api_client.request(...)
            progress.complete_stage(conn_stage)
            return result
        
        async def fallback_operation():
            progress.update_stage(
                conn_stage,
                description="Using direct service calls..."
            )
            # Show detailed progress for fallback
            with progress.add_stage("Processing...", total=100) as stage:
                result = await direct_service_call(stage)
            progress.complete_stage(conn_stage)
            return result
        
        command = SmartCommand(cli_ctx)
        result = await command.execute_with_fallback(
            http_operation,
            fallback_operation
        )
```

---

## Command-Specific Implementations

### 1. `ome package build`

**Stages**:
1. "Reading manifest..." (indeterminate, fast)
2. "Resolving files..." (indeterminate or file count)
3. "Downloading files..." (known total: X/Y files)
4. "Validating files..." (known total: X/Y files)
5. "Organizing structure..." (indeterminate)
6. "Generating metadata..." (indeterminate)

**Implementation**:
```python
async def build(ctx, manifest_file: str, ...):
    cli_ctx = ctx.obj
    cli_ctx.start_command_tracking("package-build")
    
    try:
        with cli_ctx.get_progress_manager() as progress:
            # Stage 1: Read manifest
            with progress.add_stage("Reading manifest...") as stage:
                manifest_data = await _read_manifest_file(manifest_file)
            
            # Stage 2-6: Build package
            # Note: For HTTP path, we can only show connection progress
            # For fallback path, we can show detailed progress
            
            async def http_build():
                stage = progress.add_stage("Building package via API...")
                try:
                    response = await cli_ctx.api_client.request(...)
                    return response
                finally:
                    progress.complete_stage(stage)
            
            async def fallback_build():
                # Detailed progress for direct service calls
                with progress.add_stage("Resolving files...") as resolve_stage:
                    # Count files first
                    file_count = count_files_in_manifest(manifest_data)
                
                with progress.add_stage(
                    "Downloading files...",
                    total=file_count
                ) as download_stage:
                    # Track downloads
                    for file_info in files:
                        await download_file(file_info)
                        download_stage.update(advance=1)
                
                # ... other stages ...
                
                return result
            
            command = SmartCommand(cli_ctx)
            result = await command.execute_with_fallback(
                http_build,
                fallback_build
            )
        
        await _display_build_results(cli_ctx, result, output_format)
        cli_ctx.end_command_tracking()
    except Exception as e:
        cli_ctx.log(f"Build failed: {str(e)}", "error")
        raise
```

### 2. `ome okh generate-from-url`

**Stages**:
1. "Validating URL..." (indeterminate, fast)
2. "Cloning repository..." (if --clone, indeterminate with size)
3. "Extracting project data..." (indeterminate)
4. "Analyzing files..." (known total: X/Y files)
5. "Categorizing files..." (known total: X/Y files)
   - Sub-indicator: "Using heuristics..." or "Using LLM..."
6. "Generating manifest..." (indeterminate)
   - Sub-indicator: "LLM generation..." (if LLM enabled)
7. "Reviewing manifest..." (if interactive, indeterminate)

**Implementation**:
```python
async def generate_from_url(ctx, url: str, ...):
    cli_ctx = ctx.obj
    
    with cli_ctx.get_progress_manager() as progress:
        # Stage 1: Validate URL
        with progress.add_stage("Validating URL...") as stage:
            # Quick validation
            pass
        
        # Stage 2: Clone (if enabled)
        if clone:
            with progress.add_stage("Cloning repository...") as stage:
                await clone_repository(url)
        
        # Stage 3: Extract
        with progress.add_stage("Extracting project data...") as stage:
            project_data = await extractor.extract_project(url)
        
        # Stage 4: Analyze files
        file_count = len(project_data.files)
        with progress.add_stage(
            "Analyzing files...",
            total=file_count
        ) as analyze_stage:
            for file in project_data.files:
                await analyze_file(file)
                analyze_stage.update(advance=1)
        
        # Stage 5: Categorize files
        with progress.add_stage(
            "Categorizing files...",
            total=file_count
        ) as categorize_stage:
            if use_llm:
                categorize_stage.update(
                    description="Categorizing files... [dim](Using LLM)[/dim]"
                )
            for file in project_data.files:
                await categorize_file(file, use_llm=use_llm)
                categorize_stage.update(advance=1)
        
        # Stage 6: Generate manifest
        with progress.add_stage("Generating manifest...") as gen_stage:
            if use_llm:
                gen_stage.update(
                    description="Generating manifest... [dim](LLM processing)[/dim]"
                )
            result = await engine.generate_manifest_async(project_data)
```

### 3. `ome match requirements`

**Stages**:
1. "Reading input file..." (indeterminate, fast)
2. "Extracting requirements..." (indeterminate)
3. "Loading facilities..." (indeterminate)
4. "Matching requirements..." (known total: X/Y facilities)
5. "Ranking results..." (indeterminate)

**Implementation**:
```python
async def requirements(ctx, input_file: str, ...):
    cli_ctx = ctx.obj
    
    with cli_ctx.get_progress_manager() as progress:
        # Stage 1: Read file
        with progress.add_stage("Reading input file...") as stage:
            input_data = await _read_input_file(input_file)
        
        # Stage 2: Extract requirements
        with progress.add_stage("Extracting requirements...") as stage:
            requirements = await extractor.extract_requirements(input_data)
        
        # Stage 3: Load facilities
        with progress.add_stage("Loading facilities...") as stage:
            facilities = await okw_service.list()
        
        # Stage 4: Match
        facility_count = len(facilities)
        with progress.add_stage(
            "Matching requirements...",
            total=facility_count
        ) as match_stage:
            for facility in facilities:
                await match_facility(requirements, facility)
                match_stage.update(advance=1)
        
        # Stage 5: Rank
        with progress.add_stage("Ranking results...") as stage:
            ranked_results = await rank_results(matches)
```

---

## Error Handling

### Progress Cleanup on Errors

```python
class ProgressManager:
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Always cleanup progress, even on errors"""
        try:
            if self._progress:
                self._progress.stop()
        except Exception:
            # Don't let cleanup errors mask original error
            pass
        
        # Re-raise original exception if any
        return False
```

### Error Display

When errors occur during progress:
1. Complete current stage with error indicator
2. Show error message clearly
3. Clean up progress display
4. Preserve error context

```python
try:
    with progress.add_stage("Processing...") as stage:
        await risky_operation()
except Exception as e:
    stage.update(description=f"[red]Error: {str(e)}[/red]")
    raise
```

---

## Performance Considerations

### Update Throttling

Rich.progress handles throttling via `refresh_per_second`, but we should also throttle our updates:

```python
class ProgressStage:
    def __init__(self, ...):
        self._last_update = 0.0
        self._update_interval = 0.1  # Minimum 100ms between updates
    
    def update(self, advance: float = 1.0, ...):
        """Throttle updates to avoid performance impact"""
        import time
        now = time.time()
        if now - self._last_update < self._update_interval:
            return  # Skip update if too soon
        
        self._last_update = now
        # ... perform update ...
```

### Batch Updates

For operations with many small updates:

```python
# Instead of updating on every item
for item in items:
    await process(item)
    stage.update(advance=1)  # Too frequent

# Batch updates
batch_size = max(1, len(items) // 100)  # Update ~100 times
for i, item in enumerate(items):
    await process(item)
    if i % batch_size == 0:
        stage.update(advance=batch_size)
# Final update for remainder
stage.update(advance=len(items) % batch_size)
```

---

## Testing Strategy

### Unit Tests

1. **ProgressManager Tests**:
   - Creation and initialization
   - Stage addition and management
   - Cleanup on errors
   - Disabled state (JSON mode)

2. **ProgressStage Tests**:
   - Context manager behavior
   - Update operations
   - Completion handling

3. **Helper Function Tests**:
   - `should_show_progress()` logic
   - Factory functions

### Integration Tests

1. **CLIContext Integration**:
   - Progress manager creation
   - Flag-based enabling/disabling

2. **Command Integration**:
   - Progress display in actual commands
   - Error handling during progress
   - Multi-stage operations

### Manual Testing Checklist

- [ ] Progress displays correctly in terminal
- [ ] Progress hidden in JSON mode
- [ ] Progress works with --verbose flag
- [ ] Progress handles errors gracefully
- [ ] Progress works with HTTP API path
- [ ] Progress works with direct service path
- [ ] Multi-stage progress displays correctly
- [ ] Progress cleanup on Ctrl+C
- [ ] Progress works in CI/CD (non-interactive terminals)

---

## Dependencies

### New Dependencies

Add to `requirements.txt`:
```
rich>=13.0.0
```

### Existing Dependencies

No changes to existing dependencies.

---

## Migration Plan

### Phase 1.1: Foundation (Week 1)
1. Add `rich` to requirements.txt
2. Create `src/cli/progress.py` with core classes
3. Enhance `CLIContext` with progress support
4. Add unit tests for progress utilities

### Phase 1.2: Proof of Concept (Week 1-2)
1. Implement progress in `ome package build` command
2. Test with both HTTP and fallback paths
3. Refine API based on usage

### Phase 1.3: High-Value Commands (Week 2-3)
1. Add progress to `ome package push/pull`
2. Add progress to `ome okh generate-from-url`
3. Add progress to `ome match requirements`

### Phase 1.4: Remaining Commands (Week 3-4)
1. Add progress to remaining long-running commands
2. Documentation updates
3. User testing and feedback

---

## API Reference Summary

### ProgressManager

```python
class ProgressManager:
    def __init__(cli_ctx: CLIContext, enabled: bool = True, ...)
    def __enter__() -> ProgressManager
    def __exit__(exc_type, exc_val, exc_tb) -> None
    def add_stage(description: str, total: Optional[float] = None) -> ProgressStage
    def update_stage(stage: ProgressStage, advance: float = 1.0, ...) -> None
    def complete_stage(stage: ProgressStage) -> None
    def is_enabled() -> bool
```

### ProgressStage

```python
class ProgressStage:
    def __init__(manager: ProgressManager, task_id: int, ...)
    def __enter__() -> ProgressStage
    def __exit__(exc_type, exc_val, exc_tb) -> None
    def update(advance: float = 1.0, description: Optional[str] = None) -> None
    def complete() -> None
    @property task_id() -> int
```

### Helper Functions

```python
def should_show_progress(cli_ctx: CLIContext) -> bool
def create_progress_manager(cli_ctx: CLIContext, **kwargs) -> ProgressManager
@asynccontextmanager
async def progress_stage(
    manager: ProgressManager,
    description: str,
    total: Optional[float] = None
) -> AsyncIterator[ProgressStage]
```

---

## Rich Markup Support

Progress descriptions support [Rich markup](https://rich.readthedocs.io/en/stable/markup.html):

```python
# Colored text
stage.update(description="[green]Downloading...[/green]")

# Dimmed text for sub-info
stage.update(description="Processing... [dim](Using LLM)[/dim]")

# Status indicators
stage.update(description="[yellow]Warning: Slow connection[/yellow]")
```

---

## Future Enhancements (Out of Scope for Phase 1)

1. **Service-Level Callbacks**: Pass progress callbacks to services for granular updates
2. **Metrics Integration**: Use historical data for smart ETA estimation
3. **Streaming HTTP**: Support streaming responses for HTTP API progress
4. **Progress Persistence**: Save progress state for resumable operations
5. **Custom Themes**: Allow users to customize progress appearance

---

## References

- [Rich Progress Documentation](https://rich.readthedocs.io/en/stable/reference/progress.html#)
- [Rich Markup Guide](https://rich.readthedocs.io/en/stable/markup.html)
- [Progress Indicators Review](./progress-indicators-review.md)
- [Progress Indicators Mapping](./progress-indicators-mapping.md)

