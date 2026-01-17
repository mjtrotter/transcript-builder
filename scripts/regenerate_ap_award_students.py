#!/usr/bin/env python3
"""
Regenerate transcripts for students with AP Scholar awards.
Template bug fixed: Changed {{ award }} to {{ award.type }} in template.
"""

import sys
from pathlib import Path

# Add src to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root / "src"))

from data_processor import TranscriptDataProcessor
from transcript_generator import TranscriptGenerator
from gpa_calculator import GPACalculator
from data_models import CourseWeight
import pandas as pd

# Students with AP Scholar awards (2026 seniors)
AFFECTED_STUDENTS = [
    5558999,  # Amanda Elliott - AP Scholar with Honor (25)
    6419590,  # Harrison Fretz - AP Scholar (25)
    4021159,  # Connor Hern - AP Scholar (25)
    6579181,  # Eli Iskra - AP Scholar (25)
    4021274,  # Elijah Lunden - AP Scholar (25)
    4021281,  # SaraRose Maddux - AP Scholar (25)
    7323690,  # Charlotte Sapp - AP Scholar with Honor (25)
    4021453,  # Emily Schwankoff - AP Scholar (25)
    4021552,  # Mia Wyckoff - AP Scholar (25)
]


def main():
    print("=" * 80)
    print("REGENERATING TRANSCRIPTS FOR STUDENTS WITH AP SCHOLAR AWARDS")
    print("=" * 80)
    print(f"\nTotal students to regenerate: {len(AFFECTED_STUDENTS)}\n")

    # Initialize generator
    print("Loading data...")
    generator = TranscriptGenerator(project_root)
    processor = generator.data_processor

    if not processor.load_all_data():
        print("❌ ERROR: Failed to load data")
        return

    # Setup GPA calculator
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

    # Load student details
    students_df = processor.student_details

    # Filter for affected students
    affected = students_df[students_df["User ID"].isin(AFFECTED_STUDENTS)]

    if len(affected) == 0:
        print("❌ ERROR: No matching students found!")
        return

    print(f"✅ Found {len(affected)} students to regenerate\n")

    # Output directory
    output_dir = Path.home() / "Desktop" / "Seniors"
    output_dir.mkdir(parents=True, exist_ok=True)

    successful = 0
    failed = 0

    # Generate transcripts
    for _, student in affected.iterrows():
        user_id = student["User ID"]
        first_name = student["First name"]
        last_name = student["Last name"]
        full_name = f"{first_name} {last_name}"

        print(f"Processing: {full_name} (ID: {user_id})...")

        try:
            # Generate transcript using minimalist layout
            pdf_path = generator.generate_transcript(user_id, layout="minimalist")

            if pdf_path and pdf_path.exists():
                # Copy to Desktop/Seniors
                import shutil

                dest_file = output_dir / pdf_path.name
                shutil.copy2(pdf_path, dest_file)
                print(f"  ✅ Saved to: {dest_file.name}")
                successful += 1
            else:
                print("  ❌ Failed to generate transcript")
                failed += 1

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 80)
    print("REGENERATION SUMMARY")
    print("=" * 80)
    print(f"✅ Successful: {successful}/{len(affected)}")
    if failed > 0:
        print(f"❌ Failed: {failed}/{len(affected)}")
    print(f"\n📁 Output directory: {output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
