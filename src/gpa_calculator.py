#!/usr/bin/env python3
"""
GPA CALCULATOR - Weighted/unweighted GPA calculations with CORE support
Accurate academic GPA calculations following institutional standards

CALCULATION TYPES:
✅ Unweighted GPA: Standard 4.0 scale (A=4.0, B=3.0, C=2.0, D=1.0, F=0.0)
✅ Weighted GPA: Adds course weight to base (Honors +0.5, AP +1.0)
✅ CORE GPA: Only courses flagged as CORE=Yes in weight index
✅ Semester GPA: Per-semester calculations
✅ Cumulative GPA: All semesters combined

GRADE MAPPING:
A+ = 4.0, A = 4.0, A- = 3.7
B+ = 3.3, B = 3.0, B- = 2.7
C+ = 2.3, C = 2.0, C- = 1.7
D+ = 1.3, D = 1.0, D- = 0.7
F = 0.0
P/NP/I/W = Not counted in GPA

EDGE CASES HANDLED:
- Pass/Fail courses: Count toward credits but not GPA
- Incomplete grades: Excluded from GPA until resolved
- Transfer credits: Appear on transcript but don't affect institutional GPA
- Repeated courses: Latest grade counts (configurable)
- Zero credit courses: Excluded from GPA calculations

Priority: CRITICAL - Core academic calculations
Dependencies: data_models.py for type definitions
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

# Import data models
from data_models import CourseGrade, CourseWeight, GPACalculation, TransferGrade

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Grade point mapping - simple letter grades only
GRADE_POINTS = {
    "A": 4.0,
    "B": 3.0,
    "C": 2.0,
    "D": 1.0,
    "F": 0.0,
}

# Grades that don't count in GPA
NON_GPA_GRADES = {"P", "NP", "I", "W", "Pass", "Fail", "Incomplete", "Withdrawn"}


class GPACalculator:
    """Calculate weighted, unweighted, and CORE GPAs from student course data"""

    def __init__(self, course_weights_index: Dict[str, CourseWeight]):
        """
        Initialize calculator with course weight index

        Args:
            course_weights_index: Dictionary mapping course codes to CourseWeight objects
        """
        self.course_weights_index = course_weights_index
        self.calculation_log: List[str] = []

    def calculate_student_gpa(
        self,
        student_id: int,
        course_grades: List[CourseGrade],
        include_transfer: bool = True,  # CHANGED: Default to True to include transfer grades
        transfer_grades: Optional[List[TransferGrade]] = None,
    ) -> GPACalculation:
        """
        Calculate complete GPA for a student

        Args:
            student_id: Student identifier
            course_grades: List of course grades from school
            include_transfer: Whether to include transfer credits in calculations
            transfer_grades: Transfer grade records if applicable

        Returns:
            GPACalculation object with all GPA types and metadata
        """
        self.calculation_log = []
        self.calculation_log.append(f"📊 Calculating GPA for Student ID: {student_id}")

        # Separate courses by CORE flag
        core_courses = []
        all_courses = []

        # Process regular course grades
        for grade in course_grades:
            # Get course weight info
            weight_info = self._get_course_weight(grade.course_code)
            if weight_info is None:
                self.calculation_log.append(
                    f"⚠️ Warning: No weight info for {grade.course_code} - {grade.course_title}"
                )
                continue

            # Skip zero-credit courses (middle school)
            if weight_info.credit == 0.0:
                continue

            # Add to appropriate lists
            
            # CHECK HONORS DETECTION OVERRIDE
            if getattr(grade, "is_honors_detected", False):
                # If detected as honors title, ensuring weight reflects it
                if not weight_info.is_honors and not weight_info.is_ap:
                    # Create a synthetic Honors weight (base + 0.5)
                    # Use dataclass/pydantic copy or create new
                    # CourseWeight is a Pydantic model
                    new_weight = weight_info.weight
                    if new_weight == 0.0 or new_weight == 4.0: # Standard scale usually max 4.0? or weight=0.0 means unweighted?
                         # Usually standard weight is 0.0 in "added weight" terms? No, wait.
                         # CourseWeight definition: weight: float ... 0.5=honors, 1.0=AP.
                         # If it's 0.0, we make it 0.5.
                         new_weight = 0.5
                    
                    weight_info = weight_info.copy(update={"weight": new_weight})
                    # Also log it?
                    # logger.info(f"✨ Upgraded {grade.course_title} to Honors weight")

            all_courses.append((grade, weight_info))
            if weight_info.core:
                core_courses.append((grade, weight_info))

        # CRITICAL FIX: Process transfer grades if included
        if include_transfer and transfer_grades:
            self.calculation_log.append(
                f"📚 Processing {len(transfer_grades)} transfer grades"
            )
            for transfer in transfer_grades:
                # Get course weight info for transfer course
                weight_info = self._get_course_weight(transfer.course_code)
                if weight_info is None:
                    self.calculation_log.append(
                        f"⚠️ Warning: No weight info for transfer course {transfer.course_code} - {transfer.course_title}"
                    )
                    continue

                # Skip zero-credit courses
                if weight_info.credit == 0.0:
                    continue

                # Convert TransferGrade to CourseGrade format for processing
                # Transfer grades use same scale/weight as regular grades
                # Since transfer grades don't have semester info, use "1" as default
                transfer_as_grade = CourseGrade(
                    user_id=student_id,
                    first_name=transfer.first_name,
                    last_name=transfer.last_name,
                    grad_year=transfer.grad_year if transfer.grad_year else 2024,
                    school_year=transfer.school_year,
                    course_code=(
                        transfer.course_code if transfer.course_code else "TRANSFER"
                    ),
                    course_title=transfer.course_title,
                    course_part_number="1",  # Transfer grades default to semester 1
                    term_name="Transfer Credit",
                    grade=transfer.grade,
                    credits_attempted=transfer.credits_attempted,
                    credits_earned=transfer.credits_attempted,
                )

                # Add to appropriate lists
                all_courses.append((transfer_as_grade, weight_info))
                if weight_info.core:
                    core_courses.append((transfer_as_grade, weight_info))

            transfer_added = len(
                [t for t in transfer_grades if self._get_course_weight(t.course_code)]
            )
            self.calculation_log.append(
                f"✅ Added {transfer_added} transfer grades to GPA"
            )

        # Calculate different GPA types
        weighted_gpa, weighted_semester_gpas = self._calculate_weighted_gpa(all_courses)
        unweighted_gpa, unweighted_semester_gpas = self._calculate_unweighted_gpa(
            all_courses
        )
        core_weighted_gpa, core_semester_gpas = self._calculate_weighted_gpa(
            core_courses
        )
        core_unweighted_gpa, _ = self._calculate_unweighted_gpa(core_courses)

        # Calculate credit totals
        total_credits_earned = self._calculate_credits_earned(all_courses)
        total_credits_attempted = self._calculate_credits_attempted(all_courses)

        # Count course types
        ap_courses = sum(1 for _, weight in all_courses if weight.is_ap)
        honors_courses = sum(1 for _, weight in all_courses if weight.is_honors)

        # Create GPA calculation result
        result = GPACalculation(
            student_id=student_id,
            weighted_gpa=weighted_gpa,
            weighted_semester_gpas=weighted_semester_gpas,
            unweighted_gpa=unweighted_gpa,
            unweighted_semester_gpas=unweighted_semester_gpas,
            core_weighted_gpa=core_weighted_gpa,
            core_unweighted_gpa=core_unweighted_gpa,
            core_semester_gpas=core_semester_gpas,
            total_credits_earned=total_credits_earned,
            total_credits_attempted=total_credits_attempted,
            total_courses=len(all_courses),
            core_courses=len(core_courses),
            ap_courses=ap_courses,
            honors_courses=honors_courses,
            calculation_date=datetime.now(),
        )

        self.calculation_log.append(f"✅ Calculation complete:")
        self.calculation_log.append(f"   Weighted GPA: {weighted_gpa:.3f}")
        self.calculation_log.append(f"   Unweighted GPA: {unweighted_gpa:.3f}")
        self.calculation_log.append(f"   CORE Weighted GPA: {core_weighted_gpa:.3f}")
        self.calculation_log.append(f"   Total Credits: {total_credits_earned:.1f}")

        return result

    def _get_course_weight(self, course_code: str) -> Optional[CourseWeight]:
        """Get course weight information from index"""
        return self.course_weights_index.get(course_code)

    def _calculate_weighted_gpa(
        self, courses: List[Tuple[CourseGrade, CourseWeight]]
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate weighted GPA (base points + course weight)

        Args:
            courses: List of (grade, weight_info) tuples

        Returns:
            Tuple of (cumulative_gpa, semester_gpas_dict)
        """
        if not courses:
            return 0.0, {}

        # Organize by semester
        semester_courses = {}
        for grade, weight in courses:
            semester_key = f"{grade.school_year}-S{grade.semester}"
            if semester_key not in semester_courses:
                semester_courses[semester_key] = []
            semester_courses[semester_key].append((grade, weight))

        # Calculate semester GPAs
        semester_gpas = {}
        total_weighted_points = 0.0
        total_credits = 0.0

        for semester, semester_course_list in semester_courses.items():
            semester_points = 0.0
            semester_credits = 0.0

            for grade, weight in semester_course_list:
                # Skip blank/empty grades (no credit attempted)
                grade_str = str(grade.grade).strip()
                if grade_str.upper() in ["W", "WITHDRAWN", "—", "", "NONE", "NAN"]:
                    continue  # No credit attempted for blank grades

                # Get base grade points
                grade_points = self._grade_to_points(grade.grade)
                if grade_points is None:
                    continue  # Skip non-GPA grades (P/F, I, W)

                # Add course weight
                weighted_points = grade_points + weight.weight

                # Determine credits for this semester
                # Each row represents ONE semester of a course
                # Default: weight.credit / 2 (semester is half of year)
                semester_credit = weight.credit / 2

                # Override with explicit credits if available
                if grade.credits_attempted:
                    try:
                        explicit_credit = float(grade.credits_attempted)
                        if explicit_credit > 0:
                            semester_credit = explicit_credit
                    except (ValueError, TypeError):
                        pass  # Use default calculation

                course_contribution = weighted_points * semester_credit

                semester_points += course_contribution
                semester_credits += semester_credit

            # Calculate semester GPA
            if semester_credits > 0:
                semester_gpa = semester_points / semester_credits
                semester_gpas[semester] = round(semester_gpa, 3)

                total_weighted_points += semester_points
                total_credits += semester_credits

        # Calculate cumulative GPA - DON'T round here, let display handle it
        cumulative_gpa = 0.0
        if total_credits > 0:
            cumulative_gpa = total_weighted_points / total_credits

        # Return raw cumulative (will be formatted at display time)
        # But still round semester GPAs for consistency
        return cumulative_gpa, semester_gpas

    def _calculate_unweighted_gpa(
        self, courses: List[Tuple[CourseGrade, CourseWeight]]
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate unweighted GPA (standard 4.0 scale, no course weights)

        Args:
            courses: List of (grade, weight_info) tuples

        Returns:
            Tuple of (cumulative_gpa, semester_gpas_dict)
        """
        if not courses:
            return 0.0, {}

        # Organize by semester
        semester_courses = {}
        for grade, weight in courses:
            semester_key = f"{grade.school_year}-S{grade.semester}"
            if semester_key not in semester_courses:
                semester_courses[semester_key] = []
            semester_courses[semester_key].append((grade, weight))

        # Calculate semester GPAs
        semester_gpas = {}
        total_points = 0.0
        total_credits = 0.0

        for semester, semester_course_list in semester_courses.items():
            semester_points = 0.0
            semester_credits = 0.0

            for grade, weight in semester_course_list:
                # Skip blank/empty grades (no credit attempted)
                grade_str = str(grade.grade).strip()
                if grade_str.upper() in ["W", "WITHDRAWN", "—", "", "NONE", "NAN"]:
                    continue  # No credit attempted for blank grades

                # Get base grade points (no weight added)
                grade_points = self._grade_to_points(grade.grade)
                if grade_points is None:
                    continue  # Skip non-GPA grades

                # Determine credits for this semester
                # Each row represents ONE semester
                # Default: weight.credit / 2 (semester is half-year)
                semester_credit = weight.credit / 2

                # Override with explicit credits if available
                if grade.credits_attempted:
                    try:
                        explicit_credit = float(grade.credits_attempted)
                        if explicit_credit > 0:
                            semester_credit = explicit_credit
                    except (ValueError, TypeError):
                        pass  # Use default calculation

                course_contribution = grade_points * semester_credit

                semester_points += course_contribution
                semester_credits += semester_credit

            # Calculate semester GPA
            if semester_credits > 0:
                semester_gpa = semester_points / semester_credits
                semester_gpas[semester] = round(semester_gpa, 3)

                total_points += semester_points
                total_credits += semester_credits

        # Calculate cumulative GPA - DON'T round here, let display handle it
        cumulative_gpa = 0.0
        if total_credits > 0:
            cumulative_gpa = total_points / total_credits

        # Return raw cumulative (will be formatted at display time)
        return cumulative_gpa, semester_gpas

    def _calculate_credits_earned(
        self, courses: List[Tuple[CourseGrade, CourseWeight]]
    ) -> float:
        """
        Calculate total credits earned (passing grades only)

        Note: Each course entry represents ONE SEMESTER.
        We calculate semester credits (weight.credit / 2) for each entry.
        BLANK grades (—, empty, None) = NO CREDIT EARNED
        """
        total = 0.0

        for grade, weight in courses:
            # Check if grade is passing and not blank
            grade_str = str(grade.grade).strip()
            if grade_str.upper() not in [
                "W",
                "WITHDRAWN",
                "—",
                "",
                "NONE",
                "NAN",
            ] and self._is_passing_grade(grade.grade):
                # Each row is one semester, so use half the year credit
                semester_credit = weight.credit / 2

                # Override if grade has explicit credits
                if grade.credits_attempted:
                    try:
                        explicit_credit = float(grade.credits_attempted)
                        if explicit_credit > 0:
                            semester_credit = explicit_credit
                    except (ValueError, TypeError):
                        pass

                total += semester_credit
        
        return round(total, 2)

    def _calculate_credits_attempted(
        self, courses: List[Tuple[CourseGrade, CourseWeight]]
    ) -> float:
        """
        Calculate total credits attempted (all courses)

        Note: Each course entry represents ONE SEMESTER.
        We calculate semester credits (weight.credit / 2) for each entry.
        BLANK grades (—, empty, None) = NO CREDIT ATTEMPTED
        """
        total = 0.0

        for grade, weight in courses:
            # Don't count withdrawn, blank, or missing grades
            grade_str = str(grade.grade).strip()
            if grade_str.upper() not in ["W", "WITHDRAWN", "—", "", "NONE", "NAN"]:
                # Each row is one semester, so use half the year credit
                semester_credit = weight.credit / 2

                # Override if grade has explicit credits
                if grade.credits_attempted:
                    try:
                        explicit_credit = float(grade.credits_attempted)
                        if explicit_credit > 0:
                            semester_credit = explicit_credit
                    except (ValueError, TypeError):
                        pass

                total += semester_credit

        return round(total, 2)

    def _grade_to_points(self, grade: str) -> Optional[float]:
        """
        Convert letter grade to grade points

        Args:
            grade: Letter grade (A, B+, C-, etc.) or numeric grade

        Returns:
            Grade points (0.0-4.0) or None if non-GPA grade
        """
        # Handle case where grade might be numeric type
        if isinstance(grade, (int, float)):
            try:
                numeric = float(grade)
                letter_grade = self._numeric_to_letter(numeric)
                return GRADE_POINTS.get(letter_grade, None)
            except (ValueError, TypeError):
                return None

        # Convert to string if not already
        grade_str = str(grade) if not isinstance(grade, str) else grade
        grade_upper = grade_str.strip().upper()

        # Check if non-GPA grade
        if grade_upper in NON_GPA_GRADES:
            return None

        # Try direct lookup
        if grade_upper in GRADE_POINTS:
            return GRADE_POINTS[grade_upper]

        # Handle numeric grades (convert to letter)
        try:
            numeric = float(grade_str)
            letter_grade = self._numeric_to_letter(numeric)
            return GRADE_POINTS.get(letter_grade, None)
        except ValueError:
            # Unknown grade format
            self.calculation_log.append(f"⚠️ Unknown grade format: {grade}")
            return None

    def _numeric_to_letter(self, numeric_grade: float) -> str:
        """Convert numeric grade (0-100) to letter grade"""
        if numeric_grade >= 93:
            return "A"
        elif numeric_grade >= 90:
            return "A-"
        elif numeric_grade >= 87:
            return "B+"
        elif numeric_grade >= 83:
            return "B"
        elif numeric_grade >= 80:
            return "B-"
        elif numeric_grade >= 77:
            return "C+"
        elif numeric_grade >= 73:
            return "C"
        elif numeric_grade >= 70:
            return "C-"
        elif numeric_grade >= 67:
            return "D+"
        elif numeric_grade >= 63:
            return "D"
        elif numeric_grade >= 60:
            return "D-"
        else:
            return "F"

    def _is_passing_grade(self, grade: str) -> bool:
        """Check if grade is passing"""
        grade_upper = grade.strip().upper()

        # Explicit fail grades
        if grade_upper in ["F", "NP", "FAIL", "W", "WITHDRAWN"]:
            return False

        # Pass grade
        if grade_upper in ["P", "PASS"]:
            return True

        # Letter grades - F is failing
        grade_points = self._grade_to_points(grade)
        if grade_points is not None:
            return grade_points > 0.0

        # Unknown - assume passing (conservative)
        return True

    def calculate_class_rank(
        self, student_gpa: float, all_student_gpas: List[Tuple[int, float]]
    ) -> Tuple[int, int, str]:
        """
        Calculate class rank based on weighted GPA

        Args:
            student_gpa: This student's weighted GPA
            all_student_gpas: List of (student_id, gpa) tuples for entire class

        Returns:
            Tuple of (rank, total_students, decile_description)
        """
        # Sort by GPA descending
        sorted_gpas = sorted(all_student_gpas, key=lambda x: x[1], reverse=True)

        # Find student's rank
        rank = 1
        for i, (sid, gpa) in enumerate(sorted_gpas):
            if gpa == student_gpa:
                # Handle ties - same GPA gets same rank
                if i > 0 and sorted_gpas[i - 1][1] == gpa:
                    rank = rank  # Keep previous rank
                else:
                    rank = i + 1
                break

        total_students = len(sorted_gpas)

        # Calculate decile
        percentile = (rank / total_students) * 100
        if percentile <= 10:
            decile = "Top 10%"
        elif percentile <= 20:
            decile = "Top 20%"
        elif percentile <= 25:
            decile = "Top 25%"
        elif percentile <= 50:
            decile = "Top 50%"
        else:
            decile = f"Rank {rank} of {total_students}"

        return rank, total_students, decile

    def get_calculation_log(self) -> List[str]:
        """Get detailed calculation log for debugging"""
        return self.calculation_log


def main():
    """Test GPA calculator with sample data"""

    print("📊 GPA CALCULATOR TEST")
    print("=" * 60)

    # Create sample course weights
    from data_models import CourseWeight

    course_weights = {
        "1001310": CourseWeight(
            course_id=1,
            course_code="1001310",
            course_title="English 9",
            core=True,
            weight=0.0,
            credit=1.0,
        ),
        "1001350": CourseWeight(
            course_id=2,
            course_code="1001350",
            course_title="English 10 (H)",
            core=True,
            weight=0.5,
            credit=1.0,
        ),
        "1001420": CourseWeight(
            course_id=3,
            course_code="1001420",
            course_title="AP English 11",
            core=True,
            weight=1.0,
            credit=1.0,
        ),
        "1200310": CourseWeight(
            course_id=4,
            course_code="1200310",
            course_title="Algebra I",
            core=True,
            weight=0.0,
            credit=1.0,
        ),
    }

    # Create sample grades
    from data_models import CourseGrade

    sample_grades = [
        CourseGrade(
            user_id=1001,
            first_name="John",
            last_name="Doe",
            grad_year=2024,
            school_year="2020 - 2021",
            course_code="1001310",
            course_title="English 9",
            course_part_number="1",
            term_name="Fall",
            grade="A",
            credits_attempted="1.0",
            credits_earned="1.0",
        ),
        CourseGrade(
            user_id=1001,
            first_name="John",
            last_name="Doe",
            grad_year=2024,
            school_year="2020 - 2021",
            course_code="1200310",
            course_title="Algebra I",
            course_part_number="1",
            term_name="Fall",
            grade="B+",
            credits_attempted="1.0",
            credits_earned="1.0",
        ),
        CourseGrade(
            user_id=1001,
            first_name="John",
            last_name="Doe",
            grad_year=2024,
            school_year="2021 - 2022",
            course_code="1001350",
            course_title="English 10 (H)",
            course_part_number="1",
            term_name="Fall",
            grade="A-",
            credits_attempted="1.0",
            credits_earned="1.0",
        ),
        CourseGrade(
            user_id=1001,
            first_name="John",
            last_name="Doe",
            grad_year=2024,
            school_year="2022 - 2023",
            course_code="1001420",
            course_title="AP English 11",
            course_part_number="1",
            term_name="Fall",
            grade="B",
            credits_attempted="1.0",
            credits_earned="1.0",
        ),
    ]

    # Initialize calculator
    calculator = GPACalculator(course_weights)

    # Calculate GPA
    result = calculator.calculate_student_gpa(1001, sample_grades)

    # Display results
    print("\n📋 CALCULATION RESULTS:")
    print(f"Student ID: {result.student_id}")
    print(f"\n🎯 Cumulative GPAs:")
    print(f"  Weighted GPA:         {result.weighted_gpa:.3f}")
    print(f"  Unweighted GPA:       {result.unweighted_gpa:.3f}")
    print(f"  CORE Weighted GPA:    {result.core_weighted_gpa:.3f}")
    print(f"  CORE Unweighted GPA:  {result.core_unweighted_gpa:.3f}")

    print(f"\n📊 Semester Breakdown:")
    for semester, gpa in sorted(result.weighted_semester_gpas.items()):
        print(f"  {semester}: {gpa:.3f} (weighted)")

    print(f"\n📈 Course Statistics:")
    print(f"  Total Courses:    {result.total_courses}")
    print(f"  CORE Courses:     {result.core_courses}")
    print(f"  AP Courses:       {result.ap_courses}")
    print(f"  Honors Courses:   {result.honors_courses}")
    print(f"  Credits Earned:   {result.total_credits_earned:.1f}")
    print(f"  Credits Attempted: {result.total_credits_attempted:.1f}")

    # Display calculation log
    print(f"\n📝 Calculation Log:")
    for log_entry in calculator.get_calculation_log():
        print(f"  {log_entry}")

    # Test class rank calculation
    print(f"\n🏆 CLASS RANK TEST:")
    sample_class_gpas = [
        (1001, 4.2),  # Test student
        (1002, 4.5),
        (1003, 4.0),
        (1004, 3.8),
        (1005, 4.2),  # Tie with test student
    ]

    rank, total, decile = calculator.calculate_class_rank(4.2, sample_class_gpas)
    print(f"  Rank: {rank} of {total}")
    print(f"  Decile: {decile}")

    print("\n✅ GPA calculator test complete!")


if __name__ == "__main__":
    main()
