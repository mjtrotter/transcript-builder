#!/usr/bin/env python3
"""
GPA VALIDATION TEST - Compare calculated GPAs against existing system GPAs
Validate GPA calculation methodology by comparing against student details export

COMPARISON TYPES:
✅ CORE Weighted Cumulative GPA
✅ CORE Unweighted Cumulative GPA
✅ Overall Weighted GPA (all courses including non-CORE)
✅ Overall Unweighted GPA (all courses including non-CORE)

VALIDATION METRICS:
- Exact matches (difference < 0.01)
- Close matches (difference < 0.05)
- Significant differences (difference >= 0.05)
- Missing data (no existing GPA to compare)

Priority: HIGH - Validates calculation accuracy
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from data_processor import TranscriptDataProcessor
from gpa_calculator import GPACalculator
from data_models import CourseWeight, CourseGrade


def clean_value(val):
    """Helper to handle NaN values"""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    return str(val) if val is not None else None


def validate_gpa_calculations():
    """Compare calculated GPAs against existing system GPAs"""

    print("🧪 GPA VALIDATION TEST")
    print("=" * 80)
    print("Comparing calculated GPAs against existing system GPAs")
    print()

    # Step 1: Load all data
    print("📊 STEP 1: Loading Data")
    print("-" * 80)

    data_dir = Path(__file__).parent.parent
    processor = TranscriptDataProcessor(data_dir)

    success = processor.load_all_data()
    if not success:
        print("❌ Data loading failed!")
        return False

    print(f"✅ Loaded {len(processor.student_details)} students")
    print()

    # Step 2: Build course weight index
    print("🔧 STEP 2: Building Course Weight Index")
    print("-" * 80)

    course_weights = {}
    for _, row in processor.gpa_weight_index.iterrows():
        course_code = row["course_code"]

        # Skip invalid course codes
        if not course_code or str(course_code).lower() == "nan":
            continue

        try:
            weight_obj = CourseWeight(
                course_id=int(row["courseID"]),
                course_code=str(course_code),
                course_title=str(row["course_title"]),
                core=(row["CORE"] == "Yes"),
                weight=float(row["weight"]),
                credit=float(row["credit"]),
            )
            course_weights[str(course_code)] = weight_obj
        except Exception:
            continue

    print(f"✅ Built weight index with {len(course_weights)} courses")
    print()

    # Step 3: Calculate GPAs for all students
    print("🎯 STEP 3: Calculating and Comparing GPAs")
    print("-" * 80)

    calculator = GPACalculator(course_weights)
    student_ids = processor.get_all_student_ids()

    # Results tracking
    validation_results = []
    exact_matches = 0
    close_matches = 0
    significant_diffs = 0
    missing_data = 0
    calculation_errors = 0

    print(f"Processing {len(student_ids)} students...")
    print()

    for i, student_id in enumerate(student_ids):
        student_record = processor.get_student_record(student_id)

        # Progress indicator
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(student_ids)} students...")

        # Skip students with no grades
        if not student_record.school_grades:
            continue

        # Convert grade records to CourseGrade objects
        course_grades = []
        for grade_dict in student_record.school_grades:
            try:
                course_grade = CourseGrade(
                    user_id=int(grade_dict["User ID"]),
                    first_name=grade_dict["First Name"],
                    last_name=grade_dict["Last Name"],
                    grad_year=int(grade_dict["Grad Year"]),
                    school_year=grade_dict["School Year"],
                    course_code=str(grade_dict["Course Code"]),
                    course_title=grade_dict["Course Title"],
                    course_id=None,
                    course_part_number=clean_value(
                        grade_dict.get("Course part number", "1")
                    ),
                    term_name=grade_dict["Term name"],
                    group_identifier=clean_value(grade_dict.get("Group identifier")),
                    grade=str(grade_dict["Grade"]),
                    credits_attempted=clean_value(
                        grade_dict.get("Credits Attempted", "1.0")
                    ),
                    credits_earned=clean_value(grade_dict.get("Credits Earned", "1.0")),
                    course_length=clean_value(grade_dict.get("Course length")),
                    grade_point_max=clean_value(grade_dict.get("Grade point max")),
                    points_awarded=clean_value(grade_dict.get("Points Awarded")),
                )
                course_grades.append(course_grade)
            except Exception:
                continue

        if not course_grades:
            continue

        # Calculate GPA
        try:
            gpa_result = calculator.calculate_student_gpa(
                student_id=int(student_id), course_grades=course_grades
            )

            # Get existing GPAs from student details
            existing_core_weighted = student_record.core_weighted_gpa
            existing_core_unweighted = student_record.core_unweighted_gpa

            # Check if existing GPAs are valid (not NaN)
            has_existing_weighted = existing_core_weighted is not None and not np.isnan(
                existing_core_weighted
            )
            has_existing_unweighted = (
                existing_core_unweighted is not None
                and not np.isnan(existing_core_unweighted)
            )

            # Calculate differences
            weighted_diff = None
            unweighted_diff = None
            weighted_match_status = "N/A"
            unweighted_match_status = "N/A"

            if has_existing_weighted:
                weighted_diff = abs(
                    gpa_result.core_weighted_gpa - existing_core_weighted
                )
                if weighted_diff < 0.01:
                    weighted_match_status = "EXACT"
                    exact_matches += 1
                elif weighted_diff < 0.05:
                    weighted_match_status = "CLOSE"
                    close_matches += 1
                else:
                    weighted_match_status = "DIFF"
                    significant_diffs += 1
            else:
                missing_data += 1
                weighted_match_status = "MISSING"

            if has_existing_unweighted:
                unweighted_diff = abs(
                    gpa_result.core_unweighted_gpa - existing_core_unweighted
                )
                if unweighted_diff < 0.01:
                    unweighted_match_status = "EXACT"
                elif unweighted_diff < 0.05:
                    unweighted_match_status = "CLOSE"
                else:
                    unweighted_match_status = "DIFF"
            else:
                unweighted_match_status = "MISSING"

            # Store result
            validation_results.append(
                {
                    "student_id": student_id,
                    "first_name": student_record.first_name,
                    "last_name": student_record.last_name,
                    "grad_year": student_record.graduation_year,
                    "calculated_core_weighted": gpa_result.core_weighted_gpa,
                    "existing_core_weighted": (
                        existing_core_weighted if has_existing_weighted else None
                    ),
                    "weighted_diff": weighted_diff,
                    "weighted_status": weighted_match_status,
                    "calculated_core_unweighted": gpa_result.core_unweighted_gpa,
                    "existing_core_unweighted": (
                        existing_core_unweighted if has_existing_unweighted else None
                    ),
                    "unweighted_diff": unweighted_diff,
                    "unweighted_status": unweighted_match_status,
                    "calculated_overall_weighted": gpa_result.weighted_gpa,
                    "calculated_overall_unweighted": gpa_result.unweighted_gpa,
                    "total_courses": gpa_result.total_courses,
                    "core_courses": gpa_result.core_courses,
                    "credits_earned": gpa_result.total_credits_earned,
                }
            )

        except Exception as e:
            calculation_errors += 1
            print(f"  ⚠️ Error calculating GPA for student {student_id}: {e}")
            continue

    print()
    print("✅ GPA calculation complete")
    print()

    # Step 4: Generate summary report
    print("📈 STEP 4: Validation Summary")
    print("=" * 80)

    total_compared = exact_matches + close_matches + significant_diffs

    print(f"\n📊 OVERALL STATISTICS:")
    print(f"  Total Students Processed: {len(validation_results)}")
    print(f"  Students with Existing GPAs: {total_compared}")
    print(f"  Students Missing GPA Data: {missing_data}")
    print(f"  Calculation Errors: {calculation_errors}")

    if total_compared > 0:
        print(f"\n🎯 CORE WEIGHTED GPA COMPARISON:")
        print(
            f"  ✅ Exact Matches (<0.01 diff): {exact_matches} ({exact_matches/total_compared*100:.1f}%)"
        )
        print(
            f"  ✅ Close Matches (<0.05 diff): {close_matches} ({close_matches/total_compared*100:.1f}%)"
        )
        print(
            f"  ⚠️  Significant Diffs (>=0.05): {significant_diffs} ({significant_diffs/total_compared*100:.1f}%)"
        )

        if exact_matches + close_matches > total_compared * 0.9:
            print(
                f"\n  🎉 EXCELLENT: {(exact_matches + close_matches)/total_compared*100:.1f}% within tolerance!"
            )
        elif exact_matches + close_matches > total_compared * 0.75:
            print(
                f"\n  ✅ GOOD: {(exact_matches + close_matches)/total_compared*100:.1f}% within tolerance"
            )
        else:
            print(
                f"\n  ⚠️  REVIEW NEEDED: Only {(exact_matches + close_matches)/total_compared*100:.1f}% within tolerance"
            )

    # Step 5: Show examples
    print(f"\n📝 SAMPLE COMPARISONS:")
    print("-" * 80)

    # Show exact matches
    exact_samples = [r for r in validation_results if r["weighted_status"] == "EXACT"][
        :3
    ]
    if exact_samples:
        print("\n✅ EXACT MATCHES (Examples):")
        for result in exact_samples:
            print(
                f"  {result['first_name']} {result['last_name']} ({result['grad_year']})"
            )
            print(
                f"    Calculated: {result['calculated_core_weighted']:.3f} | Existing: {result['existing_core_weighted']:.3f} | Diff: {result['weighted_diff']:.4f}"
            )

    # Show close matches
    close_samples = [r for r in validation_results if r["weighted_status"] == "CLOSE"][
        :3
    ]
    if close_samples:
        print("\n✅ CLOSE MATCHES (Examples):")
        for result in close_samples:
            print(
                f"  {result['first_name']} {result['last_name']} ({result['grad_year']})"
            )
            print(
                f"    Calculated: {result['calculated_core_weighted']:.3f} | Existing: {result['existing_core_weighted']:.3f} | Diff: {result['weighted_diff']:.4f}"
            )

    # Show significant differences
    diff_samples = [r for r in validation_results if r["weighted_status"] == "DIFF"][:5]
    if diff_samples:
        print("\n⚠️  SIGNIFICANT DIFFERENCES (Need Review):")
        for result in diff_samples:
            print(
                f"  {result['first_name']} {result['last_name']} ({result['grad_year']})"
            )
            print(
                f"    Calculated: {result['calculated_core_weighted']:.3f} | Existing: {result['existing_core_weighted']:.3f} | Diff: {result['weighted_diff']:.4f}"
            )
            print(
                f"    Courses: {result['core_courses']} CORE, {result['total_courses']} Total"
            )

    # Step 6: Save detailed results
    print(f"\n💾 STEP 5: Saving Detailed Results")
    print("-" * 80)

    results_df = pd.DataFrame(validation_results)
    output_file = data_dir / "GPA_VALIDATION_RESULTS.csv"
    results_df.to_csv(output_file, index=False)

    print(f"✅ Detailed results saved to: {output_file}")
    print(f"   Contains {len(validation_results)} student records")

    # Step 7: Analysis recommendations
    print(f"\n💡 STEP 6: Analysis & Recommendations")
    print("=" * 80)

    if significant_diffs > 0:
        print(
            f"\n⚠️  {significant_diffs} students have significant GPA differences (>= 0.05)"
        )
        print("   Possible causes:")
        print("   1. Different calculation methodologies (rounding, credit weighting)")
        print("   2. Grade replacement policy differences")
        print("   3. Course inclusion/exclusion rules")
        print("   4. Data entry errors in existing system")
        print("   5. Transfer credit handling differences")
        print("\n   📋 ACTION: Review detailed results CSV and discuss with registrar")

    if missing_data > 0:
        print(f"\n📊 {missing_data} students have no existing GPA data")
        print("   This is expected for:")
        print("   - New students with no grades yet")
        print("   - Recent enrollments")
        print("   - Students transferred to other schools")

    print("\n🎯 NEXT STEPS:")
    print("1. Review GPA_VALIDATION_RESULTS.csv for detailed comparisons")
    print("2. Investigate students with significant differences")
    print("3. Meet with registrar to validate methodology")
    print("4. Document any calculation policy differences")
    print("5. Adjust calculator if institutional policy differs")

    print("\n" + "=" * 80)
    print("✅ GPA VALIDATION TEST COMPLETE")
    print("=" * 80)

    return True


def main():
    """Run GPA validation test"""
    try:
        success = validate_gpa_calculations()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Validation test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
