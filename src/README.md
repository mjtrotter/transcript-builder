# Source Code

## Purpose
Core transcript generation logic and data processing modules.

## Contents
| File | Purpose |
|------|---------|
| data_processor.py | Load and process student data from CSV/Excel |
| data_models.py | Data classes for students, courses, grades |
| gpa_calculator.py | GPA calculation (weighted, unweighted) |
| gpa_calculator_merged.py | Alternative GPA implementation |
| transcript_generator.py | Generate HTML transcripts from templates |
| transcript_generator_minimalist.py | Simplified transcript output |

## For AI Agents

### Architecture
```
CSV/Excel → data_processor → data_models → gpa_calculator
                                              ↓
                              transcript_generator → HTML/PDF
```

### Patterns
- All data classes use `@dataclass` decorator
- GPA calculations use `Decimal` for precision (not float!)
- Template rendering uses Jinja2

### Common Issues
- **GPA precision:** Always use `Decimal` for grade calculations
- **Missing courses:** Check for None/empty in course lists
- **Template errors:** Validate context dict has all required keys

### Test Command
```bash
pytest tests/ -v
```

### Adding New Modules

1. Create module with type hints
2. Add corresponding test file in `tests/`
3. Update this README with new module description
4. Follow existing patterns (dataclasses, Decimal for numbers)
