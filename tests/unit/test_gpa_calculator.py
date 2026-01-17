"""
Unit Tests for GPA Calculator

Tests for:
- Weighted GPA calculation
- Unweighted GPA calculation
- CORE GPA calculation
- Credit calculations
- Grade point mapping
- Edge cases
"""

import pytest
from transcript_builder.core.calculators.gpa import GPACalculator
from transcript_builder.core.models import CourseGrade, CourseWeight, GPACalculation
from transcript_builder.core.models.calculations import GradingScale


class TestGPACalculator:
    """Tests for GPACalculator class"""

    def test_basic_gpa_calculation(self, sample_course_weights, sample_grades):
        """Test basic GPA calculation with standard grades"""
        calculator = GPACalculator(sample_course_weights)
        result = calculator.calculate_student_gpa(1001, sample_grades)

        assert isinstance(result, GPACalculation)
        assert result.student_id == 1001
        assert result.total_courses > 0
        assert result.weighted_gpa >= 0.0
        assert result.unweighted_gpa >= 0.0

    def test_weighted_gpa_with_honors(self, sample_course_weights):
        """Test weighted GPA with honors courses"""
        calculator = GPACalculator(sample_course_weights)

        grades = [
            CourseGrade(
                user_id=1001,
                first_name="Test",
                last_name="Student",
                grad_year=2025,
                school_year="2023 - 2024",
                course_code="ENG102H",  # Honors - weight 0.5
                course_title="English 10 Honors",
                course_part_number="1",
                term_name="Fall",
                grade="A",
                credits_attempted="0.5",
            ),
        ]

        result = calculator.calculate_student_gpa(1001, grades)

        # A in honors should be 4.0 + 0.5 = 4.5
        assert result.weighted_gpa == 4.5
        assert result.unweighted_gpa == 4.0
        assert result.honors_courses == 1

    def test_weighted_gpa_with_ap(self, sample_course_weights):
        """Test weighted GPA with AP courses"""
        calculator = GPACalculator(sample_course_weights)

        grades = [
            CourseGrade(
                user_id=1001,
                first_name="Test",
                last_name="Student",
                grad_year=2025,
                school_year="2023 - 2024",
                course_code="APENG",  # AP - weight 1.0
                course_title="AP English",
                course_part_number="1",
                term_name="Fall",
                grade="A",
                credits_attempted="0.5",
            ),
        ]

        result = calculator.calculate_student_gpa(1001, grades)

        # A in AP should be 4.0 + 1.0 = 5.0
        assert result.weighted_gpa == 5.0
        assert result.unweighted_gpa == 4.0
        assert result.ap_courses == 1

    def test_core_gpa_calculation(self, sample_course_weights):
        """Test CORE GPA only includes CORE courses"""
        calculator = GPACalculator(sample_course_weights)

        grades = [
            # CORE course (English)
            CourseGrade(
                user_id=1001,
                first_name="Test",
                last_name="Student",
                grad_year=2025,
                school_year="2023 - 2024",
                course_code="ENG101",
                course_title="English 9",
                course_part_number="1",
                term_name="Fall",
                grade="A",  # 4.0
                credits_attempted="0.5",
            ),
            # Non-CORE course (PE)
            CourseGrade(
                user_id=1001,
                first_name="Test",
                last_name="Student",
                grad_year=2025,
                school_year="2023 - 2024",
                course_code="PE101",
                course_title="Physical Education",
                course_part_number="1",
                term_name="Fall",
                grade="C",  # 2.0
                credits_attempted="0.25",
            ),
        ]

        result = calculator.calculate_student_gpa(1001, grades)

        # CORE GPA should only include English (A = 4.0)
        assert result.core_weighted_gpa == 4.0
        assert result.core_unweighted_gpa == 4.0
        assert result.core_courses == 1

        # Overall GPA should include both
        assert result.total_courses == 2

    def test_credits_earned_calculation(self, sample_course_weights):
        """Test credit calculations"""
        calculator = GPACalculator(sample_course_weights)

        grades = [
            CourseGrade(
                user_id=1001,
                first_name="Test",
                last_name="Student",
                grad_year=2025,
                school_year="2023 - 2024",
                course_code="ENG101",
                course_title="English 9",
                course_part_number="1",
                term_name="Fall",
                grade="A",
                credits_attempted="0.5",
            ),
            CourseGrade(
                user_id=1001,
                first_name="Test",
                last_name="Student",
                grad_year=2025,
                school_year="2023 - 2024",
                course_code="MATH101",
                course_title="Algebra 1",
                course_part_number="1",
                term_name="Fall",
                grade="B",
                credits_attempted="0.5",
            ),
        ]

        result = calculator.calculate_student_gpa(1001, grades)

        assert result.total_credits_earned == 1.0
        assert result.total_credits_attempted == 1.0

    def test_failing_grade_no_credit(self, sample_course_weights):
        """Test that failing grades don't earn credit"""
        calculator = GPACalculator(sample_course_weights)

        grades = [
            CourseGrade(
                user_id=1001,
                first_name="Test",
                last_name="Student",
                grad_year=2025,
                school_year="2023 - 2024",
                course_code="ENG101",
                course_title="English 9",
                course_part_number="1",
                term_name="Fall",
                grade="F",
                credits_attempted="0.5",
            ),
        ]

        result = calculator.calculate_student_gpa(1001, grades)

        assert result.total_credits_earned == 0.0
        assert result.total_credits_attempted == 0.5
        assert result.weighted_gpa == 0.0

    def test_numeric_grade_conversion(self, sample_course_weights):
        """Test conversion of numeric grades to letter grades"""
        calculator = GPACalculator(sample_course_weights)

        grades = [
            CourseGrade(
                user_id=1001,
                first_name="Test",
                last_name="Student",
                grad_year=2025,
                school_year="2023 - 2024",
                course_code="ENG101",
                course_title="English 9",
                course_part_number="1",
                term_name="Fall",
                grade="95",  # Should convert to A
                credits_attempted="0.5",
            ),
        ]

        result = calculator.calculate_student_gpa(1001, grades)

        assert result.weighted_gpa == 4.0
        assert result.unweighted_gpa == 4.0

    def test_empty_grades(self, sample_course_weights):
        """Test handling of empty grade list"""
        calculator = GPACalculator(sample_course_weights)
        result = calculator.calculate_student_gpa(1001, [])

        assert result.weighted_gpa == 0.0
        assert result.unweighted_gpa == 0.0
        assert result.total_courses == 0

    def test_custom_grading_scale(self, sample_course_weights):
        """Test custom grading scale"""
        custom_scale = GradingScale(
            grade_points={
                "A": 4.0,
                "B": 3.0,
                "C": 2.0,
                "D": 1.0,
                "F": 0.0,
            },
            honors_weight=0.75,  # Custom honors weight
            ap_weight=1.25,  # Custom AP weight
        )

        calculator = GPACalculator(sample_course_weights, grading_scale=custom_scale)

        grades = [
            CourseGrade(
                user_id=1001,
                first_name="Test",
                last_name="Student",
                grad_year=2025,
                school_year="2023 - 2024",
                course_code="ENG101",
                course_title="English 9",
                course_part_number="1",
                term_name="Fall",
                grade="A",
                credits_attempted="0.5",
            ),
        ]

        result = calculator.calculate_student_gpa(1001, grades)
        assert result.weighted_gpa == 4.0

    def test_withdrawn_grade_excluded(self, sample_course_weights):
        """Test that withdrawn grades are excluded"""
        calculator = GPACalculator(sample_course_weights)

        grades = [
            CourseGrade(
                user_id=1001,
                first_name="Test",
                last_name="Student",
                grad_year=2025,
                school_year="2023 - 2024",
                course_code="ENG101",
                course_title="English 9",
                course_part_number="1",
                term_name="Fall",
                grade="W",
                credits_attempted="0.5",
            ),
        ]

        result = calculator.calculate_student_gpa(1001, grades)

        assert result.total_credits_earned == 0.0
        assert result.total_credits_attempted == 0.0

    def test_calculation_log(self, sample_course_weights, sample_grades):
        """Test that calculation log is populated"""
        calculator = GPACalculator(sample_course_weights)
        calculator.calculate_student_gpa(1001, sample_grades)

        log = calculator.get_calculation_log()
        assert len(log) > 0
        assert any("Calculating GPA" in entry for entry in log)
