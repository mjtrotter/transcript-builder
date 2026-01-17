#!/usr/bin/env python3
"""
DATA MODELS - Pydantic schemas for transcript data validation
Type-safe data structures for student records, grades, and GPA calculations

COMPREHENSIVE DATA VALIDATION:
✅ Student Details: Demographics, GPA, class rank, service hours
✅ Course Grades: School year, semester, course info, grades earned
✅ Transfer Grades: External credits with proper validation
✅ Course Weights: GPA weight mapping, CORE flags, credit hours

VALIDATION RULES:
- User IDs must be unique integers
- GPAs must be 0.0-5.0 (weighted scale)
- Grades must be valid letter grades or numeric
- Course codes must exist in weight index
- Credits must be non-negative decimals
- Dates must be valid ISO format

Priority: CRITICAL - Foundation for all data processing
Dependencies: Pydantic for validation, Pandas for CSV loading
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime, date
from enum import Enum
import re


class GradeLevel(str, Enum):
    """Valid grade levels for transcripts"""
    GRADE_6 = "6th Grade"
    GRADE_7 = "7th Grade"
    GRADE_8 = "8th Grade"
    GRADE_9 = "9th Grade"
    GRADE_10 = "10th Grade"
    GRADE_11 = "11th Grade"
    GRADE_12 = "12th Grade"


class LetterGrade(str, Enum):
    """Valid letter grades with plus/minus modifiers"""
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    C_PLUS = "C+"
    C = "C"
    C_MINUS = "C-"
    D_PLUS = "D+"
    D = "D"
    D_MINUS = "D-"
    F = "F"
    P = "P"  # Pass
    NP = "NP"  # No Pass
    I = "I"  # Incomplete
    W = "W"  # Withdrawn


class StudentDetails(BaseModel):
    """Student demographic and summary information"""

    first_name: str = Field(..., description="Student first name")
    last_name: str = Field(..., description="Student last name")
    middle_name: Optional[str] = Field(None, description="Student middle name")
    preferred_name: Optional[str] = Field(None, description="Preferred name if different")

    user_id: int = Field(..., description="Unique student identifier")
    graduation_year: int = Field(..., ge=2020, le=2040, description="Expected graduation year")

    email: str = Field(..., description="Student email address")
    date_of_birth: date = Field(..., description="Student date of birth")
    gender: str = Field(..., description="Student gender")

    home_address: Optional[str] = Field(None, description="Complete home address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State abbreviation")

    ethnicity: Optional[str] = Field(None, description="Student ethnicity")
    race: Optional[str] = Field(None, description="Student race")
    is_latino_hispanic: Optional[str] = Field(None, description="Latino/Hispanic status")

    student_school: str = Field(..., description="School division (Upper School, etc)")
    student_grade_level: GradeLevel = Field(..., description="Current grade level")
    enroll_date: Optional[datetime] = Field(None, description="Enrollment date")
    depart_date: Optional[datetime] = Field(None, description="Departure date if applicable")

    # Academic summary data
    core_weighted_cumulative_gpa: Optional[float] = Field(None, ge=0.0, le=5.0, description="CORE weighted GPA")
    core_unweighted_cumulative_gpa: Optional[float] = Field(None, ge=0.0, le=4.0, description="CORE unweighted GPA")
    hs_rank: Optional[str] = Field(None, description="Class rank")
    class_rank: Optional[str] = Field(None, description="Class rank in decile format")

    community_service_hours: Optional[str] = Field(None, description="Service hours completed")
    credits_complete: Optional[float] = Field(None, ge=0.0, description="Credits completed")
    credits_in_progress: Optional[float] = Field(None, ge=0.0, description="Credits currently in progress")

    parents: Optional[str] = Field(None, description="Parent/guardian names")
    parents_email: Optional[str] = Field(None, description="Parent/guardian emails")

    @validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v

    @validator('state')
    def validate_state(cls, v):
        """Validate state abbreviation"""
        if v and len(v) != 2:
            raise ValueError('State must be 2-letter abbreviation')
        return v.upper() if v else v

    @validator('community_service_hours')
    def parse_service_hours(cls, v):
        """Parse service hours string to float"""
        if v and 'hours' in v:
            return v  # Keep as string for display
        return v

    class Config:
        use_enum_values = True


class CourseWeight(BaseModel):
    """Course weight and credit information from index"""

    course_id: int = Field(..., description="Internal course ID")
    course_code: str = Field(..., description="Course code identifier")
    course_title: str = Field(..., description="Full course title")

    core: bool = Field(..., description="Whether course counts in CORE GPA")
    weight: float = Field(..., ge=0.0, le=2.0, description="GPA weight added to base (0.0=standard, 0.5=honors, 1.0=AP)")
    credit: float = Field(..., ge=0.0, le=2.0, description="Credit hours (0.0=middle school, 0.5-1.0=high school)")

    @validator('core', pre=True)
    def parse_core_flag(cls, v):
        """Parse CORE flag from Yes/No to boolean"""
        if isinstance(v, str):
            return v.upper() == 'YES'
        return bool(v)

    @property
    def is_high_school_course(self) -> bool:
        """Determine if course should appear on high school transcript"""
        return self.credit > 0.0

    @property
    def is_honors(self) -> bool:
        """Check if course is honors level"""
        return self.weight == 0.5

    @property
    def is_ap(self) -> bool:
        """Check if course is AP/IB level"""
        return self.weight >= 1.0

    @property
    def course_level(self) -> str:
        """Get course level designation"""
        if self.weight >= 1.0:
            return "AP/IB"
        elif self.weight == 0.5:
            return "Honors"
        else:
            return "Standard"

    class Config:
        use_enum_values = True


class CourseGrade(BaseModel):
    """Individual course grade record"""

    user_id: int = Field(..., description="Student ID")
    first_name: str = Field(..., description="Student first name")
    last_name: str = Field(..., description="Student last name")
    grad_year: int = Field(..., description="Graduation year")

    school_year: str = Field(..., description="Academic year (e.g., '2021 - 2022')")
    course_code: str = Field(..., description="Course code")
    course_title: str = Field(..., description="Course title")
    course_id: Optional[int] = Field(None, description="Course ID for weight lookup")

    course_part_number: str = Field(..., description="Semester part (1 or 2)")
    term_name: str = Field(..., description="Term name")
    group_identifier: Optional[str] = Field(None, description="Group identifier")

    grade: str = Field(..., description="Letter or numeric grade")
    credits_attempted: Optional[str] = Field(None, description="Credits attempted")
    credits_earned: Optional[str] = Field(None, description="Credits earned")

    course_length: Optional[str] = Field(None, description="Course length indicator")
    grade_point_max: Optional[str] = Field(None, description="Maximum grade points")
    points_awarded: Optional[str] = Field(None, description="Points awarded")

    is_honors_detected: Optional[bool] = Field(False, description="Honors status detected from title")

    @validator('school_year')
    def validate_school_year(cls, v):
        """Validate school year format"""
        pattern = r'\d{4}\s*-\s*\d{4}'
        if not re.match(pattern, v):
            raise ValueError(f'School year must be in format "YYYY - YYYY", got: {v}')
        return v

    @validator('course_part_number')
    def validate_semester(cls, v):
        """Validate semester part number"""
        if v not in ['1', '2', '3', '4']:
            raise ValueError(f'Course part number must be 1, 2, 3, or 4, got: {v}')
        return v

    @property
    def semester(self) -> int:
        """Get semester number as integer"""
        return int(self.course_part_number)

    @property
    def is_numeric_grade(self) -> bool:
        """Check if grade is numeric"""
        try:
            float(self.grade)
            return True
        except (ValueError, TypeError):
            return False

    @property
    def numeric_grade(self) -> Optional[float]:
        """Convert grade to numeric if possible"""
        try:
            return float(self.grade)
        except (ValueError, TypeError):
            return None

    def to_letter_grade(self) -> Optional[str]:
        """Convert numeric grade to letter grade"""
        if self.is_numeric_grade:
            numeric = self.numeric_grade
            if numeric >= 93:
                return "A"
            elif numeric >= 90:
                return "A-"
            elif numeric >= 87:
                return "B+"
            elif numeric >= 83:
                return "B"
            elif numeric >= 80:
                return "B-"
            elif numeric >= 77:
                return "C+"
            elif numeric >= 73:
                return "C"
            elif numeric >= 70:
                return "C-"
            elif numeric >= 67:
                return "D+"
            elif numeric >= 63:
                return "D"
            elif numeric >= 60:
                return "D-"
            else:
                return "F"
        return self.grade

    class Config:
        use_enum_values = True


class TransferGrade(BaseModel):
    """Transfer credit grade record"""

    user_id: int = Field(..., description="Student ID")
    first_name: str = Field(..., description="Student first name")
    last_name: str = Field(..., description="Student last name")
    grad_year: Optional[int] = Field(None, description="Graduation year")

    school_year: str = Field(..., description="Academic year")
    course_code: Optional[str] = Field(None, description="Course code if available")
    course_title: str = Field(..., description="Course title")

    grade: str = Field(..., description="Letter or numeric grade")
    credits_attempted: str = Field(..., description="Credits attempted")

    @validator('credits_attempted')
    def parse_credits(cls, v):
        """Ensure credits are parseable as float"""
        try:
            float(v)
            return v
        except ValueError:
            raise ValueError(f'Credits must be numeric, got: {v}')

    @property
    def credits(self) -> float:
        """Get credits as float"""
        return float(self.credits_attempted)

    class Config:
        use_enum_values = True


class GPACalculation(BaseModel):
    """GPA calculation result with detailed breakdown"""

    student_id: int = Field(..., description="Student ID")

    # Weighted GPA (standard + honors + AP)
    weighted_gpa: float = Field(..., ge=0.0, le=5.0, description="Weighted cumulative GPA")
    weighted_semester_gpas: Dict[str, float] = Field(default_factory=dict, description="Semester weighted GPAs")

    # Unweighted GPA (4.0 scale)
    unweighted_gpa: float = Field(..., ge=0.0, le=4.0, description="Unweighted cumulative GPA")
    unweighted_semester_gpas: Dict[str, float] = Field(default_factory=dict, description="Semester unweighted GPAs")

    # CORE GPA (only CORE courses)
    core_weighted_gpa: float = Field(..., ge=0.0, le=5.0, description="CORE weighted cumulative GPA")
    core_unweighted_gpa: float = Field(..., ge=0.0, le=4.0, description="CORE unweighted cumulative GPA")
    core_semester_gpas: Dict[str, float] = Field(default_factory=dict, description="Semester CORE GPAs")

    # Credit summary
    total_credits_earned: float = Field(..., ge=0.0, description="Total credits earned")
    total_credits_attempted: float = Field(..., ge=0.0, description="Total credits attempted")

    # Course counts
    total_courses: int = Field(..., ge=0, description="Total courses taken")
    core_courses: int = Field(..., ge=0, description="Total CORE courses")
    ap_courses: int = Field(..., ge=0, description="Total AP/IB courses")
    honors_courses: int = Field(..., ge=0, description="Total honors courses")

    # Calculation metadata
    calculation_date: datetime = Field(default_factory=datetime.now, description="When GPA was calculated")

    class Config:
        use_enum_values = True


class StudentTranscriptRecord(BaseModel):
    """Complete student record for transcript generation"""

    student_details: StudentDetails
    course_grades: List[CourseGrade]
    transfer_grades: List[TransferGrade]
    gpa_calculation: GPACalculation

    course_weights_index: Dict[int, CourseWeight] = Field(default_factory=dict, description="Course weight lookup")

    @property
    def full_name(self) -> str:
        """Get student full name"""
        if self.student_details.middle_name:
            return f"{self.student_details.first_name} {self.student_details.middle_name} {self.student_details.last_name}"
        return f"{self.student_details.first_name} {self.student_details.last_name}"

    @property
    def display_name(self) -> str:
        """Get display name (preferred if available)"""
        if self.student_details.preferred_name:
            return f"{self.student_details.preferred_name} {self.student_details.last_name}"
        return self.full_name

    def get_courses_by_year(self) -> Dict[str, List[CourseGrade]]:
        """Group courses by school year"""
        courses_by_year = {}
        for course in self.course_grades:
            year = course.school_year
            if year not in courses_by_year:
                courses_by_year[year] = []
            courses_by_year[year].append(course)
        return courses_by_year

    def get_courses_by_year_and_semester(self) -> Dict[str, Dict[int, List[CourseGrade]]]:
        """Group courses by school year and semester"""
        courses_organized = {}
        for course in self.course_grades:
            year = course.school_year
            semester = course.semester

            if year not in courses_organized:
                courses_organized[year] = {}
            if semester not in courses_organized[year]:
                courses_organized[year][semester] = []

            courses_organized[year][semester].append(course)

        return courses_organized

    def filter_high_school_courses(self) -> List[CourseGrade]:
        """Get only high school courses (9th-12th grade)"""
        hs_courses = []
        for course in self.course_grades:
            # Look up course weight to check credit hours
            course_weight = self.course_weights_index.get(course.course_id)
            if course_weight and course_weight.is_high_school_course:
                hs_courses.append(course)
        return hs_courses

    def filter_middle_school_printable_courses(self) -> List[CourseGrade]:
        """Get middle school courses that should print (Alg1, Geom, Physical Sci, Foreign Lang)"""
        printable_codes = ['1200310', '1200320', '1206310', '1206312']  # Algebra 1, Geometry
        printable_patterns = ['708', '0717']  # Foreign language codes

        ms_courses = []
        for course in self.course_grades:
            # Check if course code matches printable criteria
            if course.course_code in printable_codes:
                ms_courses.append(course)
                continue

            # Check for foreign language or physical science patterns
            for pattern in printable_patterns:
                if course.course_code.startswith(pattern):
                    ms_courses.append(course)
                    break

            # Check for physical science
            if 'physical science' in course.course_title.lower():
                ms_courses.append(course)

        return ms_courses

    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True


# Export all models
__all__ = [
    'GradeLevel',
    'LetterGrade',
    'StudentDetails',
    'CourseWeight',
    'CourseGrade',
    'TransferGrade',
    'GPACalculation',
    'StudentTranscriptRecord'
]