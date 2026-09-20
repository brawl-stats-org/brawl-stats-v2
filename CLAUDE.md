# Development Guidelines

## Git Workflow

### Commits

**Format**: Conventional Commits

```
<type>[optional scope]: <description>

[optional body]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `chore`: Maintenance, deps, config
- `docs`: Documentation only
- `refactor`: Code restructuring, no behavior change
- `test`: Adding/updating tests
- `perf`: Performance improvement

**Scope**: Use when helpful for clarity. Examples: `feat(api):`, `fix(auth):`, `chore(deps):`

**Examples**:
```
feat: add user metrics tracking
fix(api): correct token expiry validation
chore: update dependencies
```

**Rules**:
- Single-line descriptions only (no multi-line commit messages)
- Never add co-author attribution for AI assistance

### Staging

Always ask which files to stage before committing. Do not auto-stage.

### Branches

**Format**: `type/description`

Examples:
- `feat/user-metrics`
- `fix/auth-token-validation`
- `chore/update-deps`

## GitHub Workflow

Use `gh` CLI for all issue and PR operations.

### Issues

Treat issues as tasks/tickets.

**Bug reports**:
- Expected behavior
- Actual behavior
- Reproduction steps

**Feature requests**:
- Feature description
- Major architectural changes when applicable (usually none, or close to code snippets)

### Pull Requests

Include:
- Summary of changes (what and why)
- Related issues/links

## Pipeline Scripts

### Error Handling & Logging Pattern

Pipeline scripts (data collection, uploads, artifact generation) follow a consistent pattern:

**Pattern:**
- Functions: Log errors when encountered, raise exceptions
- Main/orchestrator: Catches exceptions, sends notifications (no re-logging)

**Example:**
```python
def process_data(data, monitor=None):
    if not data:
        error_msg = "No data to process"
        if monitor:
            monitor.log_error(error_msg)
        raise ValueError(error_msg)
    # ... process

def main():
    monitor = PipelineMonitor(ntfy_topic=...)
    try:
        process_data(data, monitor)
    except Exception as e:
        # Send notification only - error already logged
        if args.notify_errors:
            monitor.send_ntfy("Task Failed", str(e), ...)
```

**Notifications:**

Use `--notify-errors` and `--notify-success` flags (optional).

Error notifications must include:
- Script name
- Operation/context
- Clear error message

Success notifications should include relevant stats.

**Logging:**

All pipeline operations log to `data/pipeline.log` via PipelineMonitor.

## Tooling

### Python

Use `uv` (Rust-based Python tooling) for all Python operations:
- Package management
- Virtual environments
- Script execution
- Dependency installation

Use `uv` commands instead of `pip`, `python -m venv`, etc.

## Documentation

### Structure

- `docs/` at root: High-level architectural/domain knowledge per system component
- Examples: `VM.md`, `DATA_COLLECTION.md`, `ARTIFACTS.md`, API integration docs
- Purpose: Explain concepts/architecture needed to work in each section

### When to Update

- Ask before creating or updating substantial documentation
- Major architectural changes warrant doc updates
- New system components need corresponding `docs/` entry

### Comments

Per code style preferences:
- Skip comments for obvious behavior
- Document: obscure algorithms, complex logic, convoluted abstractions
- Use proper doc comments (`/** */`, `///`) for public functions/classes/modules

## Working Principles

### Explain Before Acting

For non-trivial operations that modify files or affect git state, explain intent before executing unless explicitly given full control.

Prefer deliberate pace with communication over speed that requires backtracking to fix rushed decisions.
