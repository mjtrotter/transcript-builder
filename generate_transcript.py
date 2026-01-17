#!/usr/bin/env python3
"""
Simple wrapper to generate a transcript for a given student ID
Usage: python3 generate_transcript.py <student_id> <output_dir>
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print(f"Starting transcript generation...")
print(f"  Student ID: {sys.argv[1] if len(sys.argv) > 1 else 'MISSING'}")
print(f"  Output Dir: {sys.argv[2] if len(sys.argv) > 2 else 'MISSING'}")

if len(sys.argv) < 3:
    print("ERROR: Missing arguments")
    print("Usage: python3 generate_transcript.py <student_id> <output_dir>")
    sys.exit(1)

student_id = int(sys.argv[1])
output_dir = Path(sys.argv[2]).expanduser()

print(f"\nInitializing...")

# Import after adding to path
from transcript_generator import TranscriptGenerator
from gpa_calculator import GPACalculator
from data_models import CourseWeight
import pandas as pd

print("Initializing transcript generator...")
generator = TranscriptGenerator()

print("Loading all data...")
processor = generator.data_processor
processor.load_all_data()

# Initialize GPA calculator with course weights (required!)
print("Initializing GPA calculator...")
course_weights = {}
for _, row in processor.gpa_weight_index.iterrows():
    course_code = row["course_code"]
    if pd.isna(course_code):
        continue
    course_weights[course_code] = CourseWeight(
        course_id=int(row["courseID"]),
        course_code=str(course_code),
        course_title=row["course_title"],
        core=row["CORE"] == "Yes",
        weight=float(row["weight"]),
        credit=float(row["credit"]),
    )
generator.gpa_calculator = GPACalculator(course_weights)

print(f"Generating PDF for student {student_id}...")
output_path = generator.generate_transcript(user_id=student_id, layout="minimalist")

print(f"\n✅ SUCCESS!")
print(f"Transcript saved to: {output_path}")

# Copy to Desktop with correct name
import shutil

# Extract student name from the generated PDF filename
pdf_name = Path(output_path).name  # e.g., "6230206_Aruca_Roman_transcript.pdf"
desktop_path = output_dir / pdf_name
shutil.copy(output_path, desktop_path)
print(f"Also copied to: {desktop_path}")
