#!/usr/bin/env python3
"""
Export Senior Transcripts
Generates PDF transcripts for all graduating seniors and saves them to Desktop/Seniors folder
"""

import sys
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from data_processor import TranscriptDataProcessor
from transcript_generator import TranscriptGenerator


def main():
    """Export all senior transcripts to Desktop/Seniors folder"""

    # Setup paths
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    templates_dir = project_root / "templates"

    # Desktop Seniors folder
    desktop = Path.home() / "Desktop"
    output_dir = desktop / "Seniors"

    print("=" * 70)
    print("SENIOR TRANSCRIPT EXPORT")
    print("=" * 70)
    print(f"📁 Output Directory: {output_dir}")
    print()

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Created/verified output directory")
    print()

    # Initialize transcript generator (it will initialize its own data processor)
    print("📊 Loading student data...")
    generator = TranscriptGenerator(project_root)

    # Load all data through the generator's data processor
    processor = generator.data_processor

    if not processor.load_all_data():
        print("❌ ERROR: Failed to load data")
        print("\nValidation Errors:")
        for error in processor.validation_errors:
            print(f"  • {error}")
        return 1

    print(f"✅ Loaded data successfully")
    print(f"   Total students: {len(processor.student_details)}")
    print()

    # Filter for seniors (Graduation year 2026 - current seniors)
    current_year = 2026  # Seniors graduating in 2026
    seniors = processor.student_details[
        processor.student_details["Graduation year"] == current_year
    ]

    print(f"🎓 Found {len(seniors)} seniors (Graduation year {current_year})")
    print()

    if len(seniors) == 0:
        print("⚠️  No seniors found!")
        print(f"   Looking for Graduation year: {current_year}")
        print(
            f"   Available Graduation years: {sorted(processor.student_details['Graduation year'].unique())}"
        )
        return 1

    # Generator is already initialized above
    # Just need to set up GPA calculator
    from gpa_calculator import GPACalculator
    from data_models import CourseWeight
    import pandas as pd

    course_weights = {}
    for _, row in processor.gpa_weight_index.iterrows():
        course_code = row["course_code"]
        # Skip rows with NaN course codes
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

    # Generate transcripts for all seniors
    print("🔄 Generating senior transcripts...")
    print()

    successful = 0
    failed = 0

    for idx, (_, student) in enumerate(seniors.iterrows(), 1):
        user_id = student["User ID"]
        first_name = student["First name"]
        last_name = student["Last name"]

        print(
            f"[{idx}/{len(seniors)}] Processing: {first_name} {last_name} (ID: {user_id})"
        )

        try:
            # Generate transcript using minimalist layout
            pdf_path = generator.generate_transcript(user_id, layout="minimalist")

            if pdf_path and pdf_path.exists():
                # Copy to Desktop/Seniors folder
                import shutil

                dest_path = output_dir / pdf_path.name
                shutil.copy2(pdf_path, dest_path)
                print(f"   ✅ Generated: {pdf_path.name}")
                successful += 1
            else:
                print(f"   ❌ Failed to generate PDF")
                failed += 1

        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            failed += 1

        print()

    # Summary
    print("=" * 70)
    print("EXPORT COMPLETE")
    print("=" * 70)
    print(f"✅ Successful: {successful}/{len(seniors)}")
    if failed > 0:
        print(f"❌ Failed: {failed}/{len(seniors)}")
    print()
    print(f"📁 Transcripts saved to: {output_dir}")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
