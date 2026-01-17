#!/usr/bin/env python3
"""
DATA PROCESSOR - CSV loading, validation, and student record assembly
Load and validate all CSV data sources for transcript generation

DATA SOURCES:
✅ Student Details CSV - Demographics, GPA, class rank, service hours
✅ Grades CSV - All school-earned grades with semester breakdown
✅ Transfer Grades CSV - External credits and courses
✅ GPA Weight & Credit Index CSV - Course codes to weights/credits/CORE flags

VALIDATION STRATEGY:
1. Schema Validation: Ensure required columns exist with correct data types
2. Cross-Reference Validation: Verify User IDs exist across all sources
3. Data Quality Checks: Grade ranges, credit hours, course codes
4. Business Rule Validation: Handle special characters, edge cases

Priority: CRITICAL - Foundation for all transcript generation
Dependencies: pandas, pydantic for type-safe validation
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import logging

# Type validation
try:
    from pydantic import BaseModel, validator, ValidationError

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    print("Warning: pydantic not available - install for enhanced validation")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AP Exam Code Mapping (from College Board AP Datafile 2025)
AP_EXAM_CODES = {
    7: "United States History",
    10: "African American Studies",
    13: "Art History",
    14: "Drawing",
    15: "2-D Art and Design",
    16: "3-D Art and Design",
    20: "Biology",
    22: "Seminar",
    23: "Research",
    25: "Chemistry",
    28: "Chinese Language and Culture",
    31: "Computer Science A",
    32: "Computer Science Principles",
    33: "Computer Science AB",
    34: "Microeconomics",
    35: "Macroeconomics",
    36: "English Language and Composition",
    37: "English Literature and Composition",
    40: "Environmental Science",
    43: "European History",
    48: "French Language and Culture",
    51: "French Literature",
    53: "Human Geography",
    55: "German Language and Culture",
    57: "United States Government and Politics",
    58: "Comparative Government and Politics",
    60: "Latin",
    61: "Latin Literature",
    62: "Italian Language and Culture",
    64: "Japanese Language and Culture",
    65: "Precalculus",
    66: "Calculus AB",
    68: "Calculus BC",
    69: "Calculus BC: AB Subscore",
    75: "Music Theory",
    76: "Music Aural Subscore",
    77: "Music Non-Aural Subscore",
    78: "Physics B",
    80: "Physics C: Mechanics",
    82: "Physics C: Electricity and Magnetism",
    83: "Physics 1",
    84: "Physics 2",
    85: "Psychology",
    87: "Spanish Language and Culture",
    89: "Spanish Literature and Culture",
    90: "Statistics",
    93: "World History: Modern",
}

# AP Award Type Codes
AP_AWARD_CODES = {
    1: "AP Scholar",
    2: "AP Scholar with Honor",
    3: "AP Scholar with Distinction",
    4: "State AP Scholar",
    5: "National AP Scholar",
    6: "National AP Scholar (Canada)",
    7: "AP International Diploma",
    8: "DoDEA AP Scholar",
    9: "International AP Scholar",
    12: "National AP Scholar (Bermuda)",
    13: "AP Capstone Diploma",
    14: "AP Seminar and Research Certificate",
}


@dataclass
class StudentRecord:
    """Complete student record assembled from all data sources"""

    user_id: str
    first_name: str
    last_name: str
    graduation_year: int
    email: str
    home_address: str
    preferred_name: str
    middle_name: str
    parents: str
    parents_email: str
    student_school: str
    student_grade_level: str
    enroll_date: str
    gender: str
    date_of_birth: str
    ethnicity: str
    race: str
    city: str
    state: str
    core_weighted_gpa: Optional[float]
    core_unweighted_gpa: Optional[float]
    hs_rank: Optional[str]
    class_rank: Optional[str]
    community_service_hours: Optional[str]
    credits_complete: Optional[float]
    credits_in_progress: Optional[float]

    # Assembled grade data
    school_grades: List[Dict[str, Any]]
    transfer_grades: List[Dict[str, Any]]

    # Calculated fields
    calculated_weighted_gpa: Optional[float] = None
    calculated_unweighted_gpa: Optional[float] = None
    calculated_core_gpa: Optional[float] = None


class TranscriptDataProcessor:
    """Process and validate all CSV data sources for transcript generation"""

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)

        # Data storage
        self.student_details: pd.DataFrame = None
        self.grades: pd.DataFrame = None
        self.transfer_grades: pd.DataFrame = None
        self.gpa_weight_index: pd.DataFrame = None
        self.awards: pd.DataFrame = None
        self.test_scores: pd.DataFrame = None

        # New data sources for enhanced transcripts
        self.sports: pd.DataFrame = None
        self.courses_in_progress: pd.DataFrame = None
        self.ap_scores: pd.DataFrame = None
        self.sat_scores: pd.DataFrame = None
        self.act_scores: pd.DataFrame = None

        # Pre-calculated GPA results for all students
        self.gpa_results: Dict[int, Any] = {}  # user_id -> GPACalculation

        # Validation results
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []

    def load_all_data(self) -> bool:
        """Load all CSV data sources with validation"""

        logger.info("🔍 LOADING TRANSCRIPT DATA SOURCES")
        logger.info("=" * 60)

        success = True

        # Load each data source
        success &= self._load_student_details()
        success &= self._load_grades()
        success &= self._load_transfer_grades()
        success &= self._load_gpa_weight_index()

        # Load optional data sources (awards and test scores)
        self._load_awards()  # Optional - won't fail if missing
        self._load_test_scores()  # Optional - won't fail if missing

        # Load new enhanced data sources
        self._load_sports()  # Optional - sports participation
        self._load_courses_in_progress()  # Optional - current courses
        self._load_ap_scores()  # Optional - AP exam scores
        self._load_sat_scores()  # Optional - SAT scores
        self._load_act_scores()  # Optional - ACT scores

        if success:
            logger.info("✅ All data sources loaded successfully")
            self._perform_cross_validation()
            # Pre-calculate GPAs for all students
            self._calculate_all_student_gpas()
        else:
            logger.error("❌ Data loading failed - check validation errors")

        return success

    def _load_student_details(self) -> bool:
        """Load and validate student details CSV"""

        file_path = self.data_dir / "Student Details (current only).csv"

        try:
            logger.info(f"📊 Loading student details from: {file_path}")

            # Load with proper encoding
            self.student_details = pd.read_csv(file_path, encoding="utf-8-sig")

            # Derive missing columns if possible
            self._derive_missing_student_columns()

            # Validate required columns (now with relaxed requirements after derivation)
            core_required_columns = [
                "First name",
                "Last name",
                "Graduation year",
                "User ID",
                "Gender",
                "Date of birth",
            ]

            missing_core = [
                col
                for col in core_required_columns
                if col not in self.student_details.columns
            ]
            if missing_core:
                self.validation_errors.append(
                    f"Student Details missing critical columns: {missing_core}"
                )
                return False

            # Data quality checks
            self._validate_student_details_quality()

            logger.info(f"  ✅ Loaded {len(self.student_details)} student records")
            return True

        except Exception as e:
            self.validation_errors.append(f"Failed to load student details: {e}")
            logger.error(f"  ❌ Failed to load student details: {e}")
            return False

    def _derive_missing_student_columns(self):
        """Derive missing columns from existing data"""
        import re
        
        # Derive Student grade level from Graduation year if missing
        if "Student grade level" not in self.student_details.columns:
            current_year = datetime.now().year
            current_month = datetime.now().month
            # If we're past June, we're in the next school year
            school_year_end = current_year if current_month <= 6 else current_year + 1
            
            def calc_grade_level(grad_year):
                try:
                    grade = 12 - (int(grad_year) - school_year_end)
                    if 9 <= grade <= 12:
                        return f"{grade}th Grade"
                    elif grade == 1:
                        return "1st Grade"
                    elif grade == 2:
                        return "2nd Grade"
                    elif grade == 3:
                        return "3rd Grade"
                    elif 4 <= grade <= 8:
                        return f"{grade}th Grade"
                    else:
                        return "12th Grade"  # Default for alumni/invalid
                except (ValueError, TypeError):
                    return "12th Grade"
            
            self.student_details["Student grade level"] = self.student_details["Graduation year"].apply(calc_grade_level)
            logger.info("  📝 Derived 'Student grade level' from Graduation year")

        # Derive City and State from Home address if missing
        if "City" not in self.student_details.columns or "State" not in self.student_details.columns:
            def parse_city_state(address):
                if pd.isna(address) or not address:
                    return pd.Series({"City": "", "State": ""})
                
                # Try to parse "City, ST ZIPCODE" pattern from last line of address
                lines = str(address).strip().split('\n')
                if lines:
                    last_line = lines[-1].strip()
                    # Remove "United States" if present
                    last_line = last_line.replace(" United States", "").strip()
                    # Try pattern: "City, ST 12345" or "City, ST"
                    match = re.match(r'^(.+?),\s*([A-Z]{2})\s*\d*', last_line)
                    if match:
                        return pd.Series({"City": match.group(1).strip(), "State": match.group(2)})
                
                return pd.Series({"City": "", "State": ""})
            
            if "Home address" in self.student_details.columns:
                parsed = self.student_details["Home address"].apply(parse_city_state)
                if "City" not in self.student_details.columns:
                    self.student_details["City"] = parsed["City"]
                    logger.info("  📝 Derived 'City' from Home address")
                if "State" not in self.student_details.columns:
                    self.student_details["State"] = parsed["State"]
                    logger.info("  📝 Derived 'State' from Home address")
            else:
                # No address data, add empty columns
                if "City" not in self.student_details.columns:
                    self.student_details["City"] = ""
                if "State" not in self.student_details.columns:
                    self.student_details["State"] = ""
                logger.warning("  ⚠️ No Home address column - City/State will be empty")

        # Add Email column if missing (some exports don't include it)
        if "Email" not in self.student_details.columns:
            self.student_details["Email"] = ""
            logger.warning("  ⚠️ Email column not found - will be empty")

    def _load_grades(self) -> bool:
        """Load and validate grades CSV"""

        file_path = self.data_dir / "Grades.csv"

        try:
            logger.info(f"📊 Loading grades from: {file_path}")

            self.grades = pd.read_csv(file_path, encoding="utf-8-sig")

            # Validate required columns
            required_columns = [
                "User ID",
                "First Name",
                "Last Name",
                "Grad Year",
                "School Year",
                "Course Code",
                "Course Title",
                "Term name",
                "Grade",
            ]

            missing_columns = [
                col for col in required_columns if col not in self.grades.columns
            ]
            if missing_columns:
                self.validation_errors.append(
                    f"Grades missing columns: {missing_columns}"
                )
                return False

            # Data quality checks
            self._validate_grades_quality()

            # Honors Logic: Detect and Clean
            # Patterns: "Human Geography H", "Calculus (H)", "English 9 Honors"
            # Regex captures the suffix to remove it
            honors_pattern = r'\s+(\(H\)|H|Honors)$'
            
            # Create Is Honors Detected column (default False)
            self.grades["Is Honors Detected"] = False
            
            # Find matches
            mask = self.grades["Course Title"].str.contains(honors_pattern, regex=True, na=False)
            self.grades.loc[mask, "Is Honors Detected"] = True
            
            # Clean titles (remove suffix)
            self.grades["Course Title"] = self.grades["Course Title"].str.replace(honors_pattern, "", regex=True)

            logger.info(f"  ✅ Loaded {len(self.grades)} grade records")
            logger.info(f"  ✨ Detected {mask.sum()} honors courses via title scan")
            return True

        except Exception as e:
            self.validation_errors.append(f"Failed to load grades: {e}")
            logger.error(f"  ❌ Failed to load grades: {e}")
            return False

    def _load_transfer_grades(self) -> bool:
        """Load and validate transfer grades CSV"""

        file_path = self.data_dir / "Transfer Grades.csv"

        try:
            logger.info(f"📊 Loading transfer grades from: {file_path}")

            self.transfer_grades = pd.read_csv(file_path, encoding="utf-8-sig")

            # Validate required columns
            required_columns = [
                "User ID",
                "First Name",
                "Last Name",
                "Grad Year",
                "School Year",
                "Course Code",
                "Course Title",
                "Grade",
                "Credits Attempted",
            ]

            missing_columns = [
                col
                for col in required_columns
                if col not in self.transfer_grades.columns
            ]
            if missing_columns:
                self.validation_errors.append(
                    f"Transfer Grades missing columns: {missing_columns}"
                )
                return False

            # Data quality checks
            self._validate_transfer_grades_quality()

            logger.info(
                f"  ✅ Loaded {len(self.transfer_grades)} transfer grade records"
            )
            return True

        except Exception as e:
            self.validation_errors.append(f"Failed to load transfer grades: {e}")
            logger.error(f"  ❌ Failed to load transfer grades: {e}")
            return False

    def _load_gpa_weight_index(self) -> bool:
        """Load and validate GPA weight & credit index CSV"""

        file_path = self.data_dir / "GPA weight & credit index.csv"

        try:
            logger.info(f"📊 Loading GPA weight index from: {file_path}")

            self.gpa_weight_index = pd.read_csv(file_path, encoding="utf-8-sig")

            # Validate required columns
            required_columns = [
                "courseID",
                "course_code",
                "course_title",
                "CORE",
                "weight",
                "credit",
            ]

            missing_columns = [
                col
                for col in required_columns
                if col not in self.gpa_weight_index.columns
            ]
            if missing_columns:
                self.validation_errors.append(
                    f"GPA Weight Index missing columns: {missing_columns}"
                )
                return False

            # Data quality checks
            self._validate_gpa_weight_index_quality()

            logger.info(
                f"  ✅ Loaded {len(self.gpa_weight_index)} course weight mappings"
            )
            return True

        except Exception as e:
            self.validation_errors.append(f"Failed to load GPA weight index: {e}")
            logger.error(f"  ❌ Failed to load GPA weight index: {e}")
            return False

    def _load_awards(self) -> bool:
        """Load awards CSV - optional data source"""

        # Try multiple possible filenames
        possible_files = ["Sample Awards.csv", "Awards.csv", "awards_template.csv"]

        for filename in possible_files:
            file_path = self.data_dir / filename
            if file_path.exists():
                try:
                    logger.info(f"📊 Loading awards from: {file_path}")

                    self.awards = pd.read_csv(file_path, encoding="utf-8-sig")

                    # Skip comment rows
                    if "User ID" in self.awards.columns:
                        self.awards = self.awards[self.awards["User ID"].notna()]
                        self.awards = self.awards[
                            ~self.awards["User ID"].astype(str).str.startswith("#")
                        ]

                    logger.info(f"  ✅ Loaded {len(self.awards)} award records")
                    return True

                except Exception as e:
                    logger.warning(f"  ⚠️  Failed to load awards from {filename}: {e}")
                    continue

        logger.info(
            "  ℹ️  No awards file found - transcripts will generate without awards"
        )
        self.awards = pd.DataFrame()  # Empty dataframe
        return True

    def _load_test_scores(self) -> bool:
        """Load test scores CSV - optional data source"""

        # Try multiple possible filenames
        possible_files = [
            "Sample Test Scores.csv",
            "Test Scores.csv",
            "test_scores.csv",
        ]

        for filename in possible_files:
            file_path = self.data_dir / filename
            if file_path.exists():
                try:
                    logger.info(f"📊 Loading test scores from: {file_path}")

                    self.test_scores = pd.read_csv(file_path, encoding="utf-8-sig")

                    logger.info(
                        f"  ✅ Loaded {len(self.test_scores)} test score records"
                    )
                    return True

                except Exception as e:
                    logger.warning(
                        f"  ⚠️  Failed to load test scores from {filename}: {e}"
                    )
                    continue

        logger.info(
            "  ℹ️  No test scores file found - transcripts will generate without test scores"
        )
        self.test_scores = pd.DataFrame()  # Empty dataframe
        return True

    def _load_sports(self) -> bool:
        """Load sports participation CSV - optional data source"""

        file_path = self.data_dir / "Sports.csv"

        try:
            if not file_path.exists():
                logger.info(
                    "  ℹ️  No Sports.csv file found - transcripts will generate without sports"
                )
                self.sports = pd.DataFrame()
                return True

            logger.info(f"📊 Loading sports from: {file_path}")

            self.sports = pd.read_csv(file_path, encoding="utf-8-sig")

            logger.info(f"  ✅ Loaded {len(self.sports)} sports participation records")
            return True

        except Exception as e:
            logger.warning(f"  ⚠️  Failed to load sports: {e}")
            self.sports = pd.DataFrame()
            return True

    def _load_courses_in_progress(self) -> bool:
        """Load courses in progress CSV - optional data source"""

        file_path = self.data_dir / "Course in Progress.csv"

        try:
            if not file_path.exists():
                logger.info("  ℹ️  No Course in Progress file found")
                self.courses_in_progress = pd.DataFrame()
                return True

            logger.info(f"📊 Loading courses in progress from: {file_path}")

            self.courses_in_progress = pd.read_csv(file_path, encoding="utf-8-sig")

            logger.info(
                f"  ✅ Loaded {len(self.courses_in_progress)} courses in progress"
            )
            return True

        except Exception as e:
            logger.warning(f"  ⚠️  Failed to load courses in progress: {e}")
            self.courses_in_progress = pd.DataFrame()
            return True

    def _load_ap_scores(self) -> bool:
        """Load AP Student Datafile - contains cumulative AP exam scores and awards.
        
        Looks for AP Student Datafile XXXX.csv files and uses the most recent year.
        College Board files are cumulative, so the most recent file has all data.
        """

        try:
            # Find all AP datafiles and use the most recent
            ap_files = sorted(self.data_dir.glob("AP Student Datafile*.csv"), reverse=True)
            
            if not ap_files:
                logger.info("  ℹ️  No AP Student Datafile found")
                self.ap_scores = pd.DataFrame()
                return True

            # Use the most recent file (highest year number)
            file_path = ap_files[0]
            logger.info(f"📊 Loading AP scores from: {file_path.name}")

            # Load the raw file
            self.ap_scores = pd.read_csv(file_path, encoding="utf-8-sig")

            logger.info(f"  ✅ Loaded AP data for {len(self.ap_scores)} students")
            
            # Log available years of AP datafiles
            if len(ap_files) > 1:
                years = [f.stem.split()[-1] for f in ap_files]
                logger.info(f"  ℹ️  Found AP datafiles for years: {', '.join(years)}")
            
            return True

        except Exception as e:
            logger.warning(f"  ⚠️  Failed to load AP scores: {e}")
            self.ap_scores = pd.DataFrame()
            return True

    def _load_sat_scores(self) -> bool:
        """Load SAT score files - supports both old (SAT 2024.xlsx) and new (SAT Roster X.xlsx) naming"""

        try:
            sat_dfs = []

            # Try new naming convention first (SAT Roster 1.xlsx, SAT Roster 2.xlsx)
            roster_files = list(self.data_dir.glob("SAT Roster*.xlsx"))
            
            if roster_files:
                for roster_file in roster_files:
                    logger.info(f"📊 Loading SAT from: {roster_file.name}")
                    # New format: 3 header rows, then column names on row 4
                    df = pd.read_excel(roster_file, skiprows=3)
                    df = df.dropna(how="all")
                    if len(df) > 0:
                        sat_dfs.append(df)
                        logger.info(f"  ✅ Loaded {len(df)} SAT records from {roster_file.name}")
            else:
                # Fall back to old naming (SAT 2024.xlsx, SAT 2025.xlsx)
                for year in [2024, 2025, 2026]:
                    file_path = self.data_dir / f"SAT {year}.xlsx"
                    if file_path.exists():
                        logger.info(f"📊 Loading SAT {year} from: {file_path}")
                        df = pd.read_excel(file_path, skiprows=2)
                        df.columns = df.iloc[0]
                        df = df[1:].reset_index(drop=True)
                        df = df.dropna(how="all")
                        sat_dfs.append(df)
                        logger.info(f"  ✅ Loaded {len(df)} SAT {year} records")

            if sat_dfs:
                # Combine all years
                self.sat_scores = pd.concat(sat_dfs, ignore_index=True)

                # Convert score columns to numeric
                score_cols = [
                    "Total Score (400-1600)",
                    "Reading and Writing Section Score (200-800)",
                    "Math Section Score (200-800)",
                ]
                for col in score_cols:
                    if col in self.sat_scores.columns:
                        self.sat_scores[col] = pd.to_numeric(
                            self.sat_scores[col], errors="coerce"
                        )

                # Parse Student ID from the data if available
                if "School Student ID" in self.sat_scores.columns:
                    self.sat_scores["User ID"] = pd.to_numeric(
                        self.sat_scores["School Student ID"], errors="coerce"
                    )

                logger.info(
                    f"  ✅ Combined SAT data: {len(self.sat_scores)} total records"
                )
            else:
                logger.info("  ℹ️  No SAT score files found")
                self.sat_scores = pd.DataFrame()

            return True

        except Exception as e:
            logger.warning(f"  ⚠️  Failed to load SAT scores: {e}")
            self.sat_scores = pd.DataFrame()
            return True

    def _load_act_scores(self) -> bool:
        """Load ACT score files - CSV format with header rows"""

        try:
            # Find ACT files (e.g., ACT24-25.csv)
            act_files = list(self.data_dir.glob("ACT*.csv"))
            
            if not act_files:
                logger.info("  ℹ️  No ACT score files found")
                self.act_scores = pd.DataFrame()
                return True

            act_dfs = []
            for act_file in act_files:
                logger.info(f"📊 Loading ACT from: {act_file.name}")
                # ACT files have 2 header rows before the column names (row 3)
                df = pd.read_csv(act_file, skiprows=3, encoding="utf-8-sig")
                df = df.dropna(how="all")
                if len(df) > 0:
                    act_dfs.append(df)
                    logger.info(f"  ✅ Loaded {len(df)} ACT records from {act_file.name}")

            if act_dfs:
                self.act_scores = pd.concat(act_dfs, ignore_index=True)
                
                # Convert score columns to numeric
                score_cols = [
                    "ACT composite score",
                    "ACT math score",
                    "ACT science score",
                    "ACT STEM score",
                    "ACT English score",
                    "ACT reading score",
                ]
                for col in score_cols:
                    if col in self.act_scores.columns:
                        self.act_scores[col] = pd.to_numeric(
                            self.act_scores[col], errors="coerce"
                        )

                logger.info(
                    f"  ✅ Combined ACT data: {len(self.act_scores)} total records"
                )
            else:
                self.act_scores = pd.DataFrame()

            return True

        except Exception as e:
            logger.warning(f"  ⚠️  Failed to load ACT scores: {e}")
            self.act_scores = pd.DataFrame()
            return True

    def _validate_student_details_quality(self):
        """Validate student details data quality"""

        # Check for duplicate User IDs
        duplicates = self.student_details["User ID"].duplicated()
        if duplicates.any():
            duplicate_ids = self.student_details[duplicates]["User ID"].tolist()
            self.validation_errors.append(
                f"Duplicate User IDs in student details: {duplicate_ids}"
            )

        # Check graduation year range
        current_year = datetime.now().year
        invalid_grad_years = self.student_details[
            (self.student_details["Graduation year"] < current_year - 10)
            | (self.student_details["Graduation year"] > current_year + 10)
        ]
        if not invalid_grad_years.empty:
            self.validation_warnings.append(
                f"Unusual graduation years found: {invalid_grad_years['Graduation year'].unique()}"
            )

        # Check for missing critical fields
        critical_fields = ["First name", "Last name", "User ID", "Graduation year"]
        for field in critical_fields:
            missing_count = self.student_details[field].isna().sum()
            if missing_count > 0:
                self.validation_errors.append(
                    f"Missing {field} in {missing_count} student records"
                )

    def _validate_grades_quality(self):
        """Validate grades data quality"""

        # Check for valid grade values
        valid_grades = [
            "A",
            "B",
            "C",
            "D",
            "F",
            "A+",
            "A-",
            "B+",
            "B-",
            "C+",
            "C-",
            "D+",
            "D-",
            "P",
            "I",
            "W",
        ]
        # Allow numeric grades too (some might be percentages)
        invalid_grades = self.grades[
            ~self.grades["Grade"]
            .astype(str)
            .str.upper()
            .isin(valid_grades + [str(x) for x in range(0, 101)])
        ]

        if not invalid_grades.empty:
            unique_invalid = invalid_grades["Grade"].unique()
            self.validation_warnings.append(
                f"Unusual grade values found: {unique_invalid}"
            )

        # Check User ID consistency
        grade_user_ids = set(self.grades["User ID"].astype(str))
        if self.student_details is not None:
            student_user_ids = set(self.student_details["User ID"].astype(str))
            orphaned_grades = grade_user_ids - student_user_ids
            if orphaned_grades:
                self.validation_warnings.append(
                    f"Grades found for non-existent students: {len(orphaned_grades)} User IDs"
                )

    def _validate_transfer_grades_quality(self):
        """Validate transfer grades data quality"""

        # Check credits attempted values
        invalid_credits = self.transfer_grades[
            ~self.transfer_grades["Credits Attempted"]
            .astype(str)
            .str.replace(".", "")
            .str.isdigit()
        ]

        if not invalid_credits.empty:
            unique_invalid = invalid_credits["Credits Attempted"].unique()
            self.validation_warnings.append(
                f"Invalid credit values in transfer grades: {unique_invalid}"
            )

    def _validate_gpa_weight_index_quality(self):
        """Validate GPA weight index data quality"""

        # Check weight values are reasonable
        invalid_weights = self.gpa_weight_index[
            ~self.gpa_weight_index["weight"].isin([0.0, 0.5, 1.0])
        ]

        if not invalid_weights.empty:
            unique_weights = invalid_weights["weight"].unique()
            self.validation_warnings.append(
                f"Unusual weight values found: {unique_weights}"
            )

        # Check CORE flag values
        invalid_core = self.gpa_weight_index[
            ~self.gpa_weight_index["CORE"].isin(["Yes", "No"])
        ]

        if not invalid_core.empty:
            unique_core = invalid_core["CORE"].unique()
            self.validation_errors.append(f"Invalid CORE flag values: {unique_core}")

        # Check for duplicate course codes
        duplicate_codes = self.gpa_weight_index["course_code"].duplicated()
        if duplicate_codes.any():
            duplicate_list = self.gpa_weight_index[duplicate_codes][
                "course_code"
            ].tolist()
            self.validation_warnings.append(
                f"Duplicate course codes in weight index: {duplicate_list}"
            )

    def _perform_cross_validation(self):
        """Perform cross-validation between data sources"""

        logger.info("🔍 Performing cross-validation between data sources")

        # Get unique User IDs from each source
        student_ids = set(self.student_details["User ID"].astype(str))
        grade_ids = set(self.grades["User ID"].astype(str))
        transfer_ids = set(self.transfer_grades["User ID"].astype(str))

        # Check for students with grades but no details
        orphaned_grades = grade_ids - student_ids
        if orphaned_grades:
            self.validation_warnings.append(
                f"Students with grades but no details: {len(orphaned_grades)}"
            )

        # Check for students with transfer grades but no details
        orphaned_transfers = transfer_ids - student_ids
        if orphaned_transfers:
            self.validation_warnings.append(
                f"Students with transfer grades but no details: {len(orphaned_transfers)}"
            )

        # Check course code coverage
        grade_courses = set(self.grades["Course Code"].astype(str))
        weight_courses = set(self.gpa_weight_index["course_code"].astype(str))

        missing_weights = grade_courses - weight_courses
        if missing_weights:
            self.validation_warnings.append(
                f"Course codes in grades without weight mapping: {len(missing_weights)}"
            )
            logger.warning(
                f"  Missing weight mappings for: {list(missing_weights)[:10]}..."
            )  # Show first 10

    def get_ap_scores_for_student(
        self, first_name: str, last_name: str
    ) -> Dict[str, Any]:
        """
        Extract AP exam scores and awards for a student from AP Datafile 2025
        Returns dict with 'exams' list and 'awards' list
        """
        if self.ap_scores is None or self.ap_scores.empty:
            return {"exams": [], "awards": []}

        # Match student by name
        student_row = self.ap_scores[
            (
                self.ap_scores["First Name"].str.strip().str.lower()
                == first_name.strip().lower()
            )
            & (
                self.ap_scores["Last Name"].str.strip().str.lower()
                == last_name.strip().lower()
            )
        ]

        if student_row.empty:
            return {"exams": [], "awards": []}

        student_data = student_row.iloc[0]

        # Extract awards (columns 26-37: Award Type 1-6 and Award Year 1-6)
        awards = []
        col_names = list(self.ap_scores.columns)

        # Award columns start at index 25 (column 26 in 1-based indexing)
        # Pattern: Award Type 1 (idx 25), Award Year 1 (idx 26), Award Type 2 (idx 27), etc.
        for i in range(1, 7):
            # Calculate column indices (0-based)
            award_type_idx = 25 + (i - 1) * 2  # 25, 27, 29, 31, 33, 35
            award_year_idx = 26 + (i - 1) * 2  # 26, 28, 30, 32, 34, 36

            if award_type_idx >= len(student_data) or award_year_idx >= len(
                student_data
            ):
                break

            award_type_val = student_data.iloc[award_type_idx]
            award_year_val = student_data.iloc[award_year_idx]

            # Only process if we have a valid award code
            if pd.notna(award_type_val) and award_type_val != "":
                try:
                    award_code = int(float(award_type_val))
                    if award_code in AP_AWARD_CODES:
                        awards.append(
                            {
                                "type": AP_AWARD_CODES[award_code],
                                "year": (
                                    str(int(float(award_year_val)))
                                    if pd.notna(award_year_val)
                                    else ""
                                ),
                            }
                        )
                except (ValueError, TypeError):
                    continue

        # Extract AP exam scores (columns 59+, blocks of 6 columns, up to 30 exams)
        exams = []
        col_names = list(self.ap_scores.columns)

        # Start at column 59 (index 58), blocks of 6
        for exam_num in range(1, 31):  # Up to 30 exams
            base_idx = 58 + (exam_num - 1) * 6

            if base_idx + 2 >= len(col_names):
                break

            admin_year = (
                student_data.iloc[base_idx] if base_idx < len(student_data) else None
            )
            exam_code = (
                student_data.iloc[base_idx + 1]
                if base_idx + 1 < len(student_data)
                else None
            )
            exam_grade = (
                student_data.iloc[base_idx + 2]
                if base_idx + 2 < len(student_data)
                else None
            )

            # Only add if we have valid data
            if pd.notna(exam_code) and pd.notna(exam_grade):
                try:
                    code = int(float(exam_code))
                    grade = int(float(exam_grade))
                    year = str(int(float(admin_year))) if pd.notna(admin_year) else ""

                    if code in AP_EXAM_CODES and 1 <= grade <= 5:
                        exams.append(
                            {
                                "subject": AP_EXAM_CODES[code],
                                "score": grade,
                                "year": (
                                    f"20{year}" if year and len(year) == 2 else year
                                ),
                            }
                        )
                except (ValueError, TypeError):
                    continue

        return {"exams": exams, "awards": awards}

    def get_sat_superscore_for_student(
        self, student_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get SAT superscore for a student (highest EBRW + highest Math)
        Returns dict with total, ebrw, math, and test_date
        """
        if self.sat_scores is None or self.sat_scores.empty:
            return None

        # Match student by School Student ID
        student_tests = self.sat_scores[
            self.sat_scores["School Student ID"].astype(str) == str(student_id)
        ]

        if student_tests.empty:
            return None

        # Get highest EBRW score
        ebrw_col = "Reading and Writing Section Score (200-800)"
        math_col = "Math Section Score (200-800)"

        # Filter out rows with missing scores
        valid_tests = student_tests[
            student_tests[ebrw_col].notna() & student_tests[math_col].notna()
        ]

        if valid_tests.empty:
            return None

        # Get highest scores
        highest_ebrw = valid_tests[ebrw_col].max()
        highest_math = valid_tests[math_col].max()
        superscore_total = int(highest_ebrw + highest_math)

        # Get most recent test date
        if "Tested On" in valid_tests.columns:
            recent_test = valid_tests.sort_values("Tested On", ascending=False).iloc[0]
            test_date = (
                recent_test["Tested On"]
                if pd.notna(recent_test["Tested On"])
                else "Date not available"
            )
        else:
            test_date = "Date not available"

        return {
            "total": superscore_total,
            "ebrw": int(highest_ebrw),
            "math": int(highest_math),
            "test_date": test_date,
            "num_attempts": len(valid_tests),
        }

    def get_act_superscore_for_student(
        self, first_name: str, last_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get ACT superscore for a student (highest score from each section)
        ACT superscore = average of best English, Math, Reading, Science scores
        Returns dict with composite, english, math, reading, science
        """
        if self.act_scores is None or self.act_scores.empty:
            return None

        # Match student by name (ACT data uses Last Name, First Name)
        student_tests = self.act_scores[
            (self.act_scores["First Name"].str.strip().str.upper() == first_name.strip().upper())
            & (self.act_scores["Last Name"].str.strip().str.upper() == last_name.strip().upper())
        ]

        if student_tests.empty:
            return None

        # Get section scores
        eng_col = "ACT English score"
        math_col = "ACT math score"
        read_col = "ACT reading score"
        sci_col = "ACT science score"
        composite_col = "ACT composite score"

        # Filter out rows with missing composite
        valid_tests = student_tests[student_tests[composite_col].notna()]

        if valid_tests.empty:
            return None

        # Get highest scores from each section (superscore)
        highest_english = valid_tests[eng_col].max() if eng_col in valid_tests.columns else 0
        highest_math = valid_tests[math_col].max() if math_col in valid_tests.columns else 0
        highest_reading = valid_tests[read_col].max() if read_col in valid_tests.columns else 0
        highest_science = valid_tests[sci_col].max() if sci_col in valid_tests.columns else 0

        # Calculate superscore composite (average of best section scores)
        superscore_composite = round((highest_english + highest_math + highest_reading + highest_science) / 4)

        # Also get best single-sitting composite for comparison
        best_composite = int(valid_tests[composite_col].max())

        return {
            "superscore": int(superscore_composite),
            "best_composite": best_composite,
            "english": int(highest_english),
            "math": int(highest_math),
            "reading": int(highest_reading),
            "science": int(highest_science),
            "num_attempts": len(valid_tests),
        }

    def get_sports_for_student(
        self, first_name: str, last_name: str, grad_year: int
    ) -> List[Dict[str, str]]:
        """
        Get sports participation for a student
        Returns list of dicts with sport, year, and season info
        """
        if self.sports is None or self.sports.empty:
            return []

        # First filter out rows with NaN Grad Year
        valid_sports = self.sports[self.sports["Grad Year"].notna()].copy()

        # Convert Grad Year to int on the filtered data
        valid_sports["Grad Year"] = valid_sports["Grad Year"].astype(int)

        # Now match student by First Name, Last Name, and Grad Year
        student_sports = valid_sports[
            (
                valid_sports["First Name"].str.strip().str.lower()
                == first_name.strip().lower()
            )
            & (
                valid_sports["Last Name"].str.strip().str.lower()
                == last_name.strip().lower()
            )
            & (valid_sports["Grad Year"] == grad_year)
        ]

        if student_sports.empty:
            return []

        # Extract relevant columns
        sports_list = []
        for _, row in student_sports.iterrows():
            sport_entry = {
                "sport": row["Sport Level Title"] if "Sport Level Title" in row else "",
                "year": row["School Year"] if "School Year" in row else "",
                "season": row["Season"] if "Season" in row else "",
            }
            sports_list.append(sport_entry)

        return sports_list

    def get_courses_in_progress_for_student(self, user_id: str) -> List[Dict[str, str]]:
        """
        Get courses in progress for a student
        Returns list of dicts with course info
        """
        if self.courses_in_progress is None or self.courses_in_progress.empty:
            return []

        # Match student by User ID
        student_courses = self.courses_in_progress[
            self.courses_in_progress["User ID"].astype(str) == str(user_id)
        ]

        if student_courses.empty:
            return []

        # Extract relevant columns (Course title, Marking Period, School year)
        courses_list = []
        for _, row in student_courses.iterrows():
            course_entry = {
                "title": row["Course title"] if "Course title" in row else "",
                "marking_period": (
                    row["Marking Period"] if "Marking Period" in row else ""
                ),
                "school_year": row["School year"] if "School year" in row else "",
            }
            courses_list.append(course_entry)

        return courses_list

    def get_student_record(self, user_id: str) -> Optional[StudentRecord]:
        """Assemble complete student record from all data sources"""

        if self.student_details is None:
            raise ValueError("Data not loaded - call load_all_data() first")

        # Get student details
        student_row = self.student_details[
            self.student_details["User ID"].astype(str) == str(user_id)
        ]
        if student_row.empty:
            return None

        student_data = student_row.iloc[0]

        # Get school grades
        school_grades = self.grades[
            self.grades["User ID"].astype(str) == str(user_id)
        ].to_dict("records")

        # Get transfer grades
        transfer_grades = self.transfer_grades[
            self.transfer_grades["User ID"].astype(str) == str(user_id)
        ].to_dict("records")

        # Create student record
        return StudentRecord(
            user_id=str(student_data["User ID"]),
            first_name=student_data["First name"],
            last_name=student_data["Last name"],
            graduation_year=int(student_data["Graduation year"]),
            email=student_data["Email"],
            home_address=student_data["Home address"],
            preferred_name=student_data.get("Preferred Name", ""),
            middle_name=student_data.get("Middle name", ""),
            parents=student_data.get("Parents", ""),
            parents_email=student_data.get("Parents' Email", ""),
            student_school=student_data["Student school"],
            student_grade_level=student_data["Student grade level"],
            enroll_date=student_data.get("Enroll date", ""),
            gender=student_data["Gender"],
            date_of_birth=student_data["Date of birth"],
            ethnicity=student_data.get("Ethnicity", ""),
            race=student_data.get("Race", ""),
            city=student_data["City"],
            state=student_data["State"],
            core_weighted_gpa=student_data.get(
                "CORE Weighted - Cumulative GPA - Current"
            ),
            core_unweighted_gpa=student_data.get(
                "CORE Unweighted - Cumulative GPA - Current"
            ),
            hs_rank=student_data.get("HS Rank - Rank - Current"),
            class_rank=student_data.get("Class Rank"),
            community_service_hours=student_data.get("Community Service Hours"),
            credits_complete=student_data.get("Credits Complete"),
            credits_in_progress=student_data.get("Credits In Progress"),
            school_grades=school_grades,
            transfer_grades=transfer_grades,
        )

    def get_all_student_ids(self) -> List[str]:
        """Get list of all student User IDs"""

        if self.student_details is None:
            raise ValueError("Data not loaded - call load_all_data() first")

        return self.student_details["User ID"].astype(str).tolist()

    def get_course_weight_info(self, course_code: str) -> Optional[Dict[str, Any]]:
        """Get weight and credit information for a course code"""

        if self.gpa_weight_index is None:
            raise ValueError("Data not loaded - call load_all_data() first")

        course_row = self.gpa_weight_index[
            self.gpa_weight_index["course_code"] == course_code
        ]
        if course_row.empty:
            return None

        course_data = course_row.iloc[0]
        return {
            "course_id": course_data["courseID"],
            "course_code": course_data["course_code"],
            "course_title": course_data["course_title"],
            "is_core": course_data["CORE"] == "Yes",
            "weight": float(course_data["weight"]),
            "credit": float(course_data["credit"]),
        }

    def generate_validation_report(self) -> str:
        """Generate comprehensive validation report"""

        report = ["🔍 DATA VALIDATION REPORT", "=" * 50, ""]

        if not self.validation_errors and not self.validation_warnings:
            report.append("✅ All validation checks passed!")
        else:
            if self.validation_errors:
                report.append("❌ ERRORS (Must be fixed):")
                for error in self.validation_errors:
                    report.append(f"  • {error}")
                report.append("")

            if self.validation_warnings:
                report.append("⚠️ WARNINGS (Review recommended):")
                for warning in self.validation_warnings:
                    report.append(f"  • {warning}")
                report.append("")

        # Data summary
        if self.student_details is not None:
            report.append("📊 DATA SUMMARY:")
            report.append(f"  Students: {len(self.student_details)}")
            if self.grades is not None:
                report.append(f"  Grade Records: {len(self.grades)}")
            if self.transfer_grades is not None:
                report.append(f"  Transfer Records: {len(self.transfer_grades)}")
            if self.gpa_weight_index is not None:
                report.append(f"  Course Mappings: {len(self.gpa_weight_index)}")

        return "\n".join(report)

    def _calculate_all_student_gpas(self):
        """
        Pre-calculate GPAs for all students using merged dataset.
        Only processes full-time students (>4 courses).
        """
        logger.info("📊 Pre-calculating GPAs for all students from merged dataset...")

        # Import merged GPA calculator
        try:
            from gpa_calculator_merged import MergedGPACalculator
        except ImportError:
            import sys
            from pathlib import Path

            sys.path.insert(0, str(Path(__file__).parent))
            from gpa_calculator_merged import MergedGPACalculator

        # Initialize merged GPA calculator
        merged_data_path = os.path.join(self.data_dir, "Merged_Grades.csv")
        gpa_calc = MergedGPACalculator(merged_data_path)

        # Calculate GPA for each student
        full_time_count = 0
        part_time_count = 0

        for _, student in self.student_details.iterrows():
            user_id = student["User ID"]

            # Get student's CORE course count to determine full-time status
            student_courses = gpa_calc.df[
                (gpa_calc.df["User ID"] == user_id) & (gpa_calc.df["CORE"] == "Yes")
            ]
            unique_courses = len(student_courses["Course Title"].unique())

            if unique_courses < 5:
                part_time_count += 1
                continue  # Skip part-time students

            full_time_count += 1

            try:
                # Calculate cumulative GPA using merged calculator
                cum_weighted = gpa_calc.calculate_cumulative_gpa(user_id, weighted=True)
                cum_unweighted = gpa_calc.calculate_cumulative_gpa(
                    user_id, weighted=False
                )

                # Count course types for this student
                student_data = gpa_calc.df[gpa_calc.df["User ID"] == user_id]
                total_courses = len(student_data)
                core_courses = len(student_data[student_data["CORE"] == "Yes"])
                ap_courses = len(
                    student_data[
                        student_data["Course Code"].str.startswith("AP", na=False)
                    ]
                )
                honors_courses = len(student_data[student_data["Weight"] > 1.0])

                # Import data model for result storage
                try:
                    from data_models import GPACalculation
                except ImportError:
                    sys.path.insert(0, str(Path(__file__).parent))
                    from data_models import GPACalculation

                # Store GPA result with correct field names
                gpa_result = GPACalculation(
                    student_id=user_id,
                    weighted_gpa=cum_weighted["gpa"],
                    unweighted_gpa=cum_unweighted["gpa"],
                    core_weighted_gpa=cum_weighted["gpa"],
                    core_unweighted_gpa=cum_unweighted["gpa"],
                    total_credits_attempted=cum_weighted["credits_attempted"],
                    total_credits_earned=cum_weighted["credits_earned"],
                    total_courses=total_courses,
                    core_courses=core_courses,
                    ap_courses=ap_courses,
                    honors_courses=honors_courses,
                )
                self.gpa_results[user_id] = gpa_result

            except Exception as e:
                logger.error(f"Failed to calculate GPA for {user_id}: {e}")
                import traceback

                logger.error(traceback.format_exc())

        logger.info(f"  ✅ Calculated GPAs for {full_time_count} full-time students")
        logger.info(f"  ℹ️  Skipped {part_time_count} part-time students (<5 courses)")
        logger.info(
            f"  📊 Stored {len(self.gpa_results)} GPA records in gpa_results dictionary"
        )


def main():
    """Test data processor with transcript data"""

    print("🔍 TRANSCRIPT DATA PROCESSOR")
    print("=" * 50)
    print("Loading and validating all CSV data sources")
    print()

    try:
        # Initialize processor
        data_dir = Path(__file__).parent.parent
        processor = TranscriptDataProcessor(data_dir)

        # Load all data
        success = processor.load_all_data()

        # Generate validation report
        print("\n" + processor.generate_validation_report())

        if success:
            # Test with first student
            student_ids = processor.get_all_student_ids()
            if student_ids:
                test_student = processor.get_student_record(student_ids[0])
                print(f"\n🎯 TEST STUDENT RECORD:")
                print(f"Name: {test_student.first_name} {test_student.last_name}")
                print(f"Graduation Year: {test_student.graduation_year}")
                print(f"School Grades: {len(test_student.school_grades)} records")
                print(f"Transfer Grades: {len(test_student.transfer_grades)} records")

                # Test course weight lookup
                if test_student.school_grades:
                    test_course = test_student.school_grades[0]["Course Code"]
                    weight_info = processor.get_course_weight_info(test_course)
                    if weight_info:
                        print(
                            f"Sample Course: {weight_info['course_title']} (Weight: {weight_info['weight']}, Core: {weight_info['is_core']})"
                        )

            print(f"\n✅ Data processing successful!")
            return True
        else:
            print(f"\n❌ Data processing failed - check validation errors")
            return False

    except Exception as e:
        print(f"\n❌ Data processor failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Data processor failed: {e}")
        exit(1)
