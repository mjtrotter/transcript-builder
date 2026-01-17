#!/usr/bin/env python3
"""
Test V5 Transcript Features:
- Transfer credits display
- Principal's List awards
- Improved header design
- Academic year in section headers
- Decile-only rank display
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from transcript_generator import TranscriptGenerator
from gpa_calculator import GPACalculator

def main():
    print("🎓 Testing V5 Transcript Features")
    print("=" * 70)

    # Initialize generator
    generator = TranscriptGenerator(project_root)

    # Load all data
    print("\n📊 Loading student data...")
    generator.data_processor.load_all_data()
    print(f"   ✅ Loaded {len(generator.data_processor.student_details)} students")
    print(f"   ✅ Loaded {len(generator.data_processor.grades)} grade records")
    print(f"   ✅ Loaded {len(generator.data_processor.transfer_grades)} transfer credits")

    # Initialize GPA calculator
    print("\n🧮 Initializing GPA calculator...")
    course_weights = {}
    for _, row in generator.data_processor.gpa_weight_index.iterrows():
        course_weights[row["course_code"]] = type(
            "CourseWeight", (),
            {
                "credit": row["credit"],
                "weight": row["weight"],
                "core": row["CORE"] == "Yes",
                "is_ap": row["weight"] >= 1.0,
                "is_honors": 0.4 < row["weight"] < 0.9,
            },
        )()

    generator.gpa_calculator = GPACalculator(course_weights)
    print("   ✅ GPA calculator ready")

    # Calculate all GPAs for ranking system
    print("\n🏆 Calculating all student GPAs for ranking...")
    all_student_ids = generator.data_processor.student_details["User ID"].tolist()
    gpa_results = {}

    from data_models import CourseGrade
    import pandas as pd

    for user_id in all_student_ids:
        try:
            student_grades_df = generator.data_processor.grades[
                generator.data_processor.grades["User ID"] == user_id
            ]

            if len(student_grades_df) == 0:
                continue

            course_grades = []
            for _, row in student_grades_df.iterrows():
                try:
                    grade = CourseGrade(
                        user_id=int(row["User ID"]),
                        first_name=row["First Name"],
                        last_name=row["Last Name"],
                        grad_year=int(row["Grad Year"]) if pd.notna(row.get("Grad Year")) else 2025,
                        school_year=row["School Year"],
                        course_code=str(row["Course Code"]),
                        course_title=row["Course Title"],
                        course_id=int(row["Course ID"]) if pd.notna(row.get("Course ID")) else None,
                        course_part_number=str(row["Course part number"]),
                        term_name=row["Term name"],
                        grade=str(row["Grade"]),
                        credits_attempted=str(row.get("Credits attempted", "")),
                        credits_earned=str(row.get("Credits earned", "")),
                    )
                    course_grades.append(grade)
                except Exception as e:
                    continue

            if course_grades:
                gpa_result = generator.gpa_calculator.calculate_student_gpa(user_id, course_grades)
                gpa_results[user_id] = gpa_result

        except Exception as e:
            continue

    # Store GPA results in data processor for decile calculations
    generator.data_processor.gpa_results = gpa_results
    print(f"   ✅ Calculated GPAs for {len(gpa_results)} students")

    # Test students showcasing new features
    test_students = [
        (4021037, "Isabella D'Altilio - Senior with 12 transfer credits"),
        (4020963, "Zachary Bingham - Potential Principal's List (all A's S2)"),
    ]

    print(f"\n📝 Generating V5 transcripts for {len(test_students)} students:\n")

    for user_id, description in test_students:
        try:
            print(f"  Generating: {description}")
            output_path = generator.generate_transcript(
                user_id=user_id,
                transcript_type='Official',
                layout='v5'  # Use V5 layout
            )
            print(f"  ✅ Generated: {output_path.name}\n")
        except Exception as e:
            print(f"  ❌ Error for student {user_id}: {str(e)}\n")
            import traceback
            traceback.print_exc()

    print("✅ V5 transcript generation test complete!")
    print(f"\nCheck output at: {project_root / 'output' / 'test_transcripts'}")
    print("\n📋 Expected features to verify in PDFs:")
    print("  ✓ Isabella: Transfer credits section with source schools")
    print("  ✓ Zachary: Principal's List award if criteria met")
    print("  ✓ Both: Watermark fully visible (not cut off)")
    print("  ✓ Both: OFFICIAL/TRANSCRIPT stacked in header")
    print("  ✓ Both: Academic year in section headers")
    print("  ✓ Both: Decile-only rank display (not actual rank number)")
    print("  ✓ Both: CORE GPA: weighted(unweighted) format")

if __name__ == "__main__":
    main()
