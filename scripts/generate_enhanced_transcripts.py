#!/usr/bin/env python3
"""
Generate Enhanced Transcripts with All Features
- AP scores from 2025 datafile with awards
- SAT superscore (highest EBRW + highest Math)
- Sports participation
- Courses in progress
- 1-page layout for grades 9-10
- 2-page layout for grades 11-12 with test scores and honors
"""

import sys
from pathlib import Path

# Add src directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from data_processor import TranscriptDataProcessor
from gpa_calculator import GPACalculator
from transcript_generator import TranscriptGenerator
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Generate transcripts for test students"""

    print("\n" + "=" * 70)
    print("ENHANCED TRANSCRIPT GENERATION")
    print("=" * 70 + "\n")

    # Initialize transcript generator (it will initialize its own data processor)
    print("📊 Initializing transcript generator...")
    generator = TranscriptGenerator(project_root)

    # Load all data through the generator's data processor
    processor = generator.data_processor
    print("📊 Loading data sources...")
    success = processor.load_all_data()

    if not success:
        print("\n❌ Failed to load data. Check errors above.")
        return False

    # Initialize GPA calculator with course weights
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

    print("\n✅ All data sources loaded successfully!\n")

    # Test students to generate (students with AP scores)
    test_students = [
        6230206,  # Roman Aruca (Grade 12 - has AP data)
        4020963,  # Zachary Bingham (Grade 11 - has AP data)
        4021037,  # Isabella D'Altilio (Grade 12 - senior)
    ]

    print(f"🎓 Generating transcripts for {len(test_students)} test students...\n")

    for user_id in test_students:
        try:
            # Get student info
            student_row = processor.student_details[
                processor.student_details["User ID"] == user_id
            ]

            if student_row.empty:
                print(f"⚠️  Student {user_id} not found")
                continue

            student_data = student_row.iloc[0]
            first_name = student_data["First name"]
            last_name = student_data["Last name"]
            grade_level = student_data["Student grade level"]
            grad_year = int(student_data["Graduation year"])

            print(f"👤 {first_name} {last_name} (Grade {grade_level})")
            print(f"   User ID: {user_id}")
            print(f"   Grad Year: {grad_year}")

            # Get AP scores
            ap_data = processor.get_ap_scores_for_student(first_name, last_name)
            if ap_data["exams"]:
                print(f"   📚 AP Exams: {len(ap_data['exams'])} total")
                for exam in ap_data["exams"][:3]:  # Show first 3
                    print(
                        f"      - {exam['subject']}: {exam['score']} ({exam['year']})"
                    )
                if len(ap_data["exams"]) > 3:
                    print(f"      ... and {len(ap_data['exams']) - 3} more")

            if ap_data["awards"]:
                print(f"   🏆 AP Awards:")
                for award in ap_data["awards"]:
                    print(f"      - {award['type']} (20{award['year']})")

            # Get SAT superscore
            sat_data = processor.get_sat_superscore_for_student(user_id)
            if sat_data:
                print(f"   📊 SAT Superscore: {sat_data['total']}")
                print(f"      EBRW: {sat_data['ebrw']} | Math: {sat_data['math']}")
                print(f"      Attempts: {sat_data['num_attempts']}")

            # Get sports
            sports = processor.get_sports_for_student(first_name, last_name, grad_year)
            if sports:
                print(f"   ⚽ Sports: {len(sports)} participation records")
                unique_sports = set(s["sport"] for s in sports)
                print(f"      {', '.join(list(unique_sports)[:3])}")

            # Get courses in progress
            courses_ip = processor.get_courses_in_progress_for_student(user_id)
            if courses_ip:
                print(f"   📝 Courses in Progress: {len(courses_ip)}")

            # Generate transcript
            print(f"   🖨️  Generating transcript...")

            output_path = generator.generate_transcript(user_id, layout="minimalist")

            if output_path:
                print(f"   ✅ Transcript saved: {output_path}\n")
            else:
                print(f"   ❌ Failed to generate transcript\n")

        except Exception as e:
            print(f"   ❌ Error generating transcript: {e}\n")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 70)
    print("✅ TRANSCRIPT GENERATION COMPLETE")
    print("=" * 70 + "\n")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
