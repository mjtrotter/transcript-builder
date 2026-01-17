<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# please give me this output as an MD file that I can drop into vs code or in a copyable text format

Below is the complete AP Student Datafile Interpretation Guide in markdown format, ready to be copied directly into VS Code or any text editor. All tables and content are formatted for compatibility with markdown parsers and documentation systems.[^1]

***

# AP Student Datafile 2025: Interpretation Guide

This document outlines how to programmatically read the AP Student Datafile (2025), including explicit mappings for award types and AP exam codes, enabling automated extraction of award and AP exam score information.

## General File Structure

- The datafile is a double-quoted CSV with 244 columns.
- Student demographic and AP performance data is provided in identified columns.


## Student and Award Columns

| Column | Name | Description |
| :-- | :-- | :-- |
| 1 | AP Number / AP ID | Unique student AP identifier |
| 2 | Last Name | Student's surname |
| 3 | First Name | Student's given name |
| 26-37 | Award Type 1-6 / Year 1-6 | Six award slots; see award code mapping below |

### Award Type Codes

| Code | Award Description |
| :-- | :-- |
| 01 | AP Scholar |
| 02 | AP Scholar with Honor |
| 03 | AP Scholar with Distinction |
| 04 | State AP Scholar |
| 05 | National AP Scholar |
| 06 | National AP Scholar (Canada) |
| 07 | AP International Diploma |
| 08 | DoDEA AP Scholar |
| 09 | International AP Scholar |
| 12 | National AP Scholar (Bermuda) |
| 13 | AP Capstone Diploma |
| 14 | AP Seminar and Research Certificate |

- Award year is provided as a two-digit year in the adjacent columns.


## AP Exam Results Columns

- Exams are grouped into blocks of six columns per test; the first block starts at column 59.
- Exam block fields are:
    - Admin Year XX (last two digits of year)
    - Exam Code XX (subject code)
    - Exam Grade XX (score: 1-5)
    - Irregularity Code \#1 XX
    - Irregularity Code \#2 XX
    - Class Section Code XX (blank)


### AP Exam Code Mapping

| Code | AP Subject |
| :-- | :-- |
| 7 | United States History |
| 10 | African American Studies |
| 13 | Art History |
| 14 | Drawing |
| 15 | 2-D Art and Design |
| 16 | 3-D Art and Design |
| 20 | Biology |
| 22 | Seminar |
| 23 | Research |
| 25 | Chemistry |
| 28 | Chinese Language and Culture |
| 31 | Computer Science A |
| 32 | Computer Science Principles |
| 33 | Computer Science AB |
| 34 | Microeconomics |
| 35 | Macroeconomics |
| 36 | English Language and Composition |
| 37 | English Literature and Composition |
| 40 | Environmental Science |
| 43 | European History |
| 48 | French Language and Culture |
| 51 | French Literature |
| 53 | Human Geography |
| 55 | German Language and Culture |
| 57 | United States Government and Politics |
| 58 | Comparative Government and Politics |
| 60 | Latin |
| 61 | Latin Literature |
| 62 | Italian Language and Culture |
| 64 | Japanese Language and Culture |
| 65 | Precalculus |
| 66 | Calculus AB |
| 68 | Calculus BC |
| 69 | Calculus BC: AB Subscore |
| 75 | Music Theory |
| 76 | Music Aural Subscore |
| 77 | Music Non-Aural Subscore |
| 78 | Physics B |
| 80 | Physics C: Mechanics |
| 82 | Physics C: Electricity and Magnetism |
| 83 | Physics 1 |
| 84 | Physics 2 |
| 85 | Psychology |
| 87 | Spanish Language and Culture |
| 89 | Spanish Literature and Culture |
| 90 | Statistics |
| 93 | World History: Modern |

Codes not listed may refer to discontinued exams.

## Automated Data Extraction Logic

### For Extracting Awards

- For each student row, scan columns 26, 28, 30, 32, 34, 36 for award codes.
- Map each code per above table; obtain year from adjacent award year columns (27, 29, 31, 33, 35, 37).


### For Extracting AP Exam Scores

- For each exam block (starts at column 59, increments by six), read:
    - Admin Year
    - Exam Code, mapped to subject using above table
    - Exam Grade (Score 1–5)
- Repeat for all blocks up to 30 exams per student.


### Example Extraction Output

```json
{
  "student_id": "...",
  "awards": [
    {"type": "AP Scholar with Honor", "year": "23"},
    {"type": "AP Capstone Diploma", "year": "24"}
  ],
  "ap_exams": [
    {"year": "24", "subject": "English Language and Composition", "score": 5},
    {"year": "23", "subject": "United States History", "score": 4}
  ]
}
```


## Notes on Other Fields

- Ignore "Class Section Code" columns.
- Irregularity codes are only relevant for special exam events—see College Board data definitions as needed.
- Race/ethnicity values are located in columns 243–244.

***

This document serves as a ready-to-use schema for AI agents and automated data workflows targeting the AP Student Datafile (2025).[^1]

<div align="center">⁂</div>

[^1]: https://apcentral.collegeboard.org/media/pdf/ap-datafile-layout-2025.pdf

