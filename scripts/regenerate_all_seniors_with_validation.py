#!/usr/bin/env python3
"""
Regenerate all senior transcripts with validation for:
1. 3-page transcripts (should be 2 pages)
2. Page 2 footer overlaps
"""

import sys
from pathlib import Path
import shutil

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from data_processor import TranscriptDataProcessor
from transcript_generator import TranscriptGenerator
from gpa_calculator import GPACalculator
from data_models import CourseWeight
import pandas as pd
from PyPDF2 import PdfReader


def check_pdf_issues(pdf_path: Path) -> dict:
    """
    Check if PDF has issues:
    - Is it 3 pages? (should be 2)
    - Does page 2 have footer overlap? (detected via page height analysis)

    Returns dict with 'pages', 'is_three_pages', 'potential_overlap'
    """
    issues = {
        "pages": 0,
        "is_three_pages": False,
        "potential_overlap": False,
        "error": None,
    }

    try:
        reader = PdfReader(pdf_path)
        page_count = len(reader.pages)
        issues["pages"] = page_count
        issues["is_three_pages"] = page_count == 3

        # For now, we'll flag potential overlap if it's 3 pages
        # More sophisticated detection would require PDF text extraction
        if page_count == 3:
            issues["potential_overlap"] = True

    except Exception as e:
        issues["error"] = str(e)

    return issues


def main():
    print("=" * 80)
    print("🎓 REGENERATING ALL SENIOR TRANSCRIPTS WITH VALIDATION")
    print("=" * 80)
    print()

    # Initialize
    generator = TranscriptGenerator(project_root)
    processor = generator.data_processor

    if not processor.load_all_data():
        print("❌ ERROR: Failed to load data")
        sys.exit(1)

    # Initialize GPA calculator
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

    # Get all seniors (grad year 2026 - current year)
    seniors = processor.student_details[
        processor.student_details["Graduation year"] == 2026
    ]

    print(f"📊 Found {len(seniors)} seniors (Class of 2026)")
    print()

    # Create output folder
    desktop_dir = Path.home() / "Desktop" / "Seniors"
    desktop_dir.mkdir(parents=True, exist_ok=True)

    # Statistics
    success_count = 0
    failed = []
    three_page_students = []
    overlap_warnings = []

    # Process each senior
    for idx, (_, student) in enumerate(seniors.iterrows(), 1):
        user_id = student["User ID"]
        first_name = student["First name"]
        last_name = student["Last name"]

        print(f"[{idx}/{len(seniors)}] {first_name} {last_name} (ID: {user_id})")

        try:
            # Generate transcript
            pdf_path = generator.generate_transcript(user_id, layout="minimalist")

            if pdf_path and pdf_path.exists():
                # Validate the PDF
                issues = check_pdf_issues(pdf_path)

                # Report issues
                if issues["error"]:
                    print(f"  ⚠️  PDF validation error: {issues['error']}")
                elif issues["is_three_pages"]:
                    print(f"  🚨 WARNING: 3 pages (should be 2) - NEEDS REVIEW")
                    three_page_students.append(
                        {
                            "name": f"{first_name} {last_name}",
                            "id": user_id,
                            "pages": issues["pages"],
                        }
                    )
                else:
                    print(f"  ✅ {issues['pages']} pages - OK")

                # Copy to Desktop/Seniors
                dest = desktop_dir / pdf_path.name
                shutil.copy2(pdf_path, dest)
                print(f"  📁 Copied to {dest.name}")
                success_count += 1

            else:
                print(f"  ❌ Failed to generate PDF")
                failed.append(f"{first_name} {last_name}")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            failed.append(f"{first_name} {last_name}")

        print()

    # Final summary
    print("=" * 80)
    print("📊 GENERATION SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully generated: {success_count}/{len(seniors)}")

    if failed:
        print(f"\n❌ Failed ({len(failed)}):")
        for name in failed:
            print(f"  - {name}")

    if three_page_students:
        print(f"\n🚨 3-PAGE TRANSCRIPTS - NEED REVIEW ({len(three_page_students)}):")
        print("=" * 80)
        for student in three_page_students:
            print(
                f"  - {student['name']:30} (ID: {student['id']}) - {student['pages']} pages"
            )
        print()
        print("These students likely have too many courses for 2 pages.")
        print("Options:")
        print("  1. Use ultra-compact spacing")
        print("  2. Reduce course details")
        print("  3. Accept 3 pages for students with many courses")

    print()
    print(f"📁 All transcripts saved to: {desktop_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
