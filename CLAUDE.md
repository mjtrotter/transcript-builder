# Transcript Builder

## Stack
- Language: Python
- Framework: Jinja2 (templating), WeasyPrint (PDF)
- Database: SQLite (student data)
- Test: `pytest tests/`
- Build: `python -m build`

## Coding Rules
- Type hints required for all functions
- No hardcoded paths or credentials
- Error handling for all file/data operations
- Follow existing patterns in src/

## Test Policy
- Run tests before commit: `pytest tests/`
- Coverage target: 80%
- TDD for new features: write tests first

## Delegation Rules

**Claude (orchestrator) handles:**
- Planning and architecture decisions
- Updating documentation (READMEs, STATUS.md)
- Code review and final approval
- Template debugging (HTML/CSS)
- GPA calculation logic review

**Delegate to executors:**
- Code generation (>20 lines) → use `delegate_code` tool
- Research queries → use `delegate_research` tool
- Always provide `context_files` to prevent hallucination

**Routing priority:**
1. Jules: Multi-file refactors, complex features (15/day)
2. Gemini CLI: Most code generation (1500/day)
3. QwenAgent: Fallback, data processing (unlimited)

## MCP Tools

```
delegate_code(task, context_files, output_path, executor="auto")
delegate_research(query, output_path, mode="deep")
delegation_status()
run_tests(test_command, working_dir)
```

## Folder README Protocol

Every folder has a README.md with:
- Purpose (1 sentence)
- Contents table (file → purpose)
- For AI Agents section (patterns, test commands, common issues)

Update READMEs when adding/modifying files.

## Scratchpad

`_scratch/` is for ephemeral session coordination:
- `current_task.md` - Active work description
- `delegation_log.md` - What was delegated and results
- `test_failures.md` - Current failures to fix

Clean up scratchpad at session end.

## Project Notes

This system generates academic transcripts from student data:
- Input: CSV/Excel student records, course data
- Output: HTML/PDF transcripts
- Key modules: `src/data_processor.py`, `src/gpa_calculator.py`, `src/transcript_generator.py`
- Templates in `templates/` (Jinja2 HTML)
- Watch for GPA precision issues (use Decimal, not float)
