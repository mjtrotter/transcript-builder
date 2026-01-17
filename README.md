# Transcript Builder

> Student transcript generation system - creates academic transcripts from student data.

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run tests
pytest tests/

# Generate a transcript
python generate_transcript.py --student-id 12345
```

## Project Structure

```
transcript-builder/
├── .claude/              # AI orchestration config
│   ├── settings.json     # MCP servers and tools
│   ├── delegation/       # Delegation toolkit
│   └── skills/           # Reusable skills (TDD, debug, etc.)
├── src/                  # Source code
│   ├── data_processor.py # Load and process student data
│   ├── gpa_calculator.py # GPA calculation logic
│   └── transcript_generator.py # Generate HTML/PDF output
├── templates/            # Jinja2 HTML templates
├── data/                 # Student data files
├── tests/                # Test files
├── planning/             # Project status and session logs
└── _scratch/             # Ephemeral session coordination
```

## Development Workflow

1. **Check status:** Read `planning/STATUS.md`
2. **Understand code:** Read folder READMEs before modifying
3. **Use TDD:** Write tests first for new features
4. **Delegate:** Use `delegate_code` for code generation
5. **Update docs:** Update READMEs when adding/changing files

## AI Orchestration

This project uses the Delegation Toolkit for AI-assisted development:

- **Jules:** Complex multi-file changes (15/day)
- **Gemini CLI:** Fast code generation (1500/day)
- **QwenAgent:** Local fallback (unlimited)
- **Perplexity:** Research queries

See `CLAUDE.md` for detailed delegation rules.

## Key Features

- CSV/Excel data import
- GPA calculation (weighted, unweighted)
- HTML transcript generation
- PDF export via WeasyPrint
- Batch processing support

## License

MIT
