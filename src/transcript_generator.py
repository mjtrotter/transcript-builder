#!/usr/bin/env python3
"""
TRANSCRIPT GENERATOR - Main PDF generation engine
Generate professional PDF transcripts from student data

GENERATION PROCESS:
1. Load student data from CSV sources
2. Calculate GPA and class rank
3. Render HTML template with student data
4. Convert HTML to PDF using ReportLab/WeasyPrint
5. Add watermarks and security features
6. Save to output directory

FEATURES:
✅ Professional template rendering
✅ GPA calculations integrated
✅ Class rank display
✅ Awards and honors sections
✅ Transfer credit handling
✅ Watermark support
✅ PDF/A compliance

Priority: HIGH - Core transcript generation
Dependencies: Jinja2, WeasyPrint, ReportLab, data_processor, gpa_calculator
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Template engine
from jinja2 import Environment, FileSystemLoader, select_autoescape

# PDF generation
try:
    from weasyprint import HTML, CSS

    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("WeasyPrint not available - install for PDF generation")

# Import our modules
import pandas as pd
from data_processor import TranscriptDataProcessor
from gpa_calculator import GPACalculator
from class_rank_calculator import ClassRankCalculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranscriptGenerator:
    """Generate professional PDF transcripts"""

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize transcript generator

        Args:
            project_root: Path to project root directory
        """
        if project_root is None:
            self.project_root = Path(__file__).parent.parent
        else:
            self.project_root = Path(project_root)

        self.templates_dir = self.project_root / "templates"
        self.output_dir = self.project_root / "output"
        self.assets_dir = self.project_root / "assets"

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Add custom filter to list dictionary keys
        def list_keys_filter(d):
            if isinstance(d, dict):
                return list(d.keys())
            return []

        self.env.filters["list_keys"] = list_keys_filter

        # Load data processor
        self.data_processor = TranscriptDataProcessor(self.project_root / "data")

        # Initialize calculators
        self.gpa_calculator = None
        self.rank_calculator = None

        logger.info(f"Transcript generator initialized")
        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Templates: {self.templates_dir}")
        logger.info(f"Output: {self.output_dir}")

    def generate_transcript(
        self,
        user_id: int,
        transcript_type: str = "Official",
        output_filename: Optional[str] = None,
        layout: str = "landscape",
    ) -> Path:
        """
        Generate transcript PDF for a single student

        Args:
            user_id: Student ID
            transcript_type: "Official" or "Unofficial"
            output_filename: Custom filename (optional)

        Returns:
            Path to generated PDF file
        """
        logger.info(f"📄 Generating {transcript_type} transcript for student {user_id}")

        # Load student data from dataframe
        student_df = self.data_processor.student_details[
            self.data_processor.student_details["User ID"] == user_id
        ]

        if len(student_df) == 0:
            raise ValueError(f"Student {user_id} not found")

        student_record = student_df.iloc[0].to_dict()

        # Get student grades as list of dicts
        student_grades_df = self.data_processor.grades[
            self.data_processor.grades["User ID"] == user_id
        ]

        # Convert to list for GPA calculator
        from data_models import CourseGrade

        course_grades = []
        for _, row in student_grades_df.iterrows():
            try:
                grade = CourseGrade(
                    user_id=int(row["User ID"]),
                    first_name=row["First Name"],
                    last_name=row["Last Name"],
                    grad_year=int(row["Grad Year"]),
                    school_year=row["School Year"],
                    course_code=str(row["Course Code"]),
                    course_title=row["Course Title"],
                    course_id=(
                        int(row["Course ID"])
                        if pd.notna(row.get("Course ID"))
                        else None
                    ),
                    course_part_number=str(row["Course part number"]),
                    term_name=row["Term name"],
                    grade=str(row["Grade"]),
                    credits_attempted=str(row.get("Credits attempted", "")),
                    credits_earned=str(row.get("Credits earned", "")),
                    is_honors_detected=bool(row.get("Is Honors Detected", False)),
                )
                course_grades.append(grade)
            except Exception as e:
                logger.warning(f"Skipping grade record: {e}")
                continue

        # Get GPA from pre-calculated results (transfer grades included)
        # Fall back to on-the-fly calculation only if not available
        if user_id in self.data_processor.gpa_results:
            gpa = self.data_processor.gpa_results[user_id]
            logger.info(
                f"✅ Using pre-calculated GPA for student {user_id}: "
                f"W={gpa.weighted_gpa:.3f}, UW={gpa.unweighted_gpa:.3f}"
            )
        else:
            logger.warning(
                f"⚠️  No pre-calculated GPA for student {user_id}, "
                f"calculating on-the-fly"
            )
            gpa = self.gpa_calculator.calculate_student_gpa(user_id, course_grades)

        # Calculate class rank
        class_rank = None
        if self.rank_calculator and user_id in self.rank_calculator.rankings:
            class_rank = self.rank_calculator.get_student_rank(user_id)

        # Prepare template data
        if layout == "minimalist" or layout == "v5" or layout == "v4" or layout == "v3":
            from transcript_generator_minimalist import prepare_minimalist_template_data

            template_data = prepare_minimalist_template_data(
                student_record,
                gpa,
                self.data_processor,
                self.gpa_calculator,
                self.project_root,
            )
        elif layout == "v2":
            # Use V2 template with proper grade mapping and YTD GPAs
            template_data = self._prepare_v2_template_data(
                student_record, gpa, class_rank, transcript_type
            )
        elif layout == "landscape":
            template_data = self._prepare_landscape_template_data(
                student_record, gpa, class_rank, transcript_type
            )
        else:
            template_data = self._prepare_template_data(
                student_record, gpa, class_rank, transcript_type
            )

        # Render HTML
        html_content = self._render_html(template_data, layout)

        # Generate PDF
        if output_filename is None:
            last_name = student_record.get(
                "Last name", student_record.get("last_name", "Student")
            )
            first_name = student_record.get(
                "First name", student_record.get("first_name", "")
            )
            output_filename = f"{user_id}_{last_name}_{first_name}_transcript.pdf"

        output_path = self.output_dir / "test_transcripts" / output_filename

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if WEASYPRINT_AVAILABLE:
            self._generate_pdf_weasyprint(html_content, output_path, layout)
        else:
            # Fallback: save HTML for manual conversion
            html_path = output_path.with_suffix(".html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.warning(f"WeasyPrint not available - saved HTML to {html_path}")
            return html_path

        logger.info(f"✅ Transcript generated: {output_path}")
        return output_path

    def _prepare_template_data(
        self,
        student_record: Dict[str, Any],
        gpa: Any,
        class_rank: Optional[Any],
        transcript_type: str,
    ) -> Dict[str, Any]:
        """Prepare data dictionary for template rendering"""

        # Get student ID from record
        student_id = student_record["User ID"]

        # Determine student grade level for each school year
        grad_year = student_record.get("Grad Year", student_record.get("grad_year"))
        current_grade = student_record.get(
            "Student Grade Level", student_record.get("student_grade_level", 12)
        )

        # Organize courses by year with semester grades side-by-side
        courses_by_year = {}

        # Get grades for this student
        student_grades_df = self.data_processor.grades[
            self.data_processor.grades["User ID"] == student_id
        ]

        # Group courses by year and course code to combine semesters
        year_course_map = {}

        for _, grade_row in student_grades_df.iterrows():
            year = grade_row["School Year"]
            course_code = str(grade_row["Course Code"])
            semester = int(grade_row["Course part number"])

            if year not in year_course_map:
                year_course_map[year] = {}

            if course_code not in year_course_map[year]:
                # Get weight info
                weight_info = self.gpa_calculator.course_weights_index.get(course_code)

                year_course_map[year][course_code] = {
                    "course_code": course_code,
                    "course_title": grade_row["Course Title"],
                    "sem1_grade": None,
                    "sem2_grade": None,
                    "weight": (
                        weight_info
                        if weight_info
                        else type(
                            "W",
                            (),
                            {
                                "credit": 0.0,
                                "weight": 0.0,
                                "is_ap": False,
                                "is_honors": False,
                            },
                        )()
                    ),
                }

            # Assign grade to appropriate semester
            if semester == 1:
                year_course_map[year][course_code]["sem1_grade"] = grade_row["Grade"]
            elif semester == 2:
                year_course_map[year][course_code]["sem2_grade"] = grade_row["Grade"]

        # Convert to final structure with grade levels
        for year in sorted(year_course_map.keys(), reverse=True):
            # Calculate grade level for this year
            # Example: "2023-2024" -> extract 2024, compare with grad_year
            year_parts = year.split("-")
            if len(year_parts) == 2:
                end_year = int(year_parts[1])
                grade_level = (
                    12 - (grad_year - end_year) if grad_year else current_grade
                )
            else:
                grade_level = current_grade

            courses_by_year[year] = {
                "grade_level": grade_level,
                "courses": list(year_course_map[year].values()),
            }

        # School information (customize these)
        school_info = {
            "school_name": "Keswick Christian School",
            "school_address": "8585 66th Street North, Pinellas Park, FL 33782",
            "school_phone": "(727) 522-5115",
            "school_website": "www.keswickchristian.org",
            "registrar_name": "Dr. School Registrar",
            "school_logo_path": str(self.assets_dir / "logos" / "school_logo.png"),
        }

        template_data = {
            # Student information
            "student": student_record,
            # Academic data
            "courses_by_year": courses_by_year,
            "semester_gpas": gpa.weighted_semester_gpas,
            "gpa": gpa,
            "class_rank": class_rank,
            # Transfer credits
            "transfer_credits": [],
            # Awards (placeholder - will be populated from awards CSV)
            "awards": [],
            "awards_by_year": {},
            # Document metadata
            "transcript_type": transcript_type,
            "issue_date": datetime.now().strftime("%B %d, %Y"),
            "verification_code": self._generate_verification_code(
                student_record["User ID"]
            ),
            # School information
            **school_info,
        }

        return template_data

    def _sort_courses_core_first(self, courses: List[Dict]) -> List[Dict]:
        """Sort courses with CORE courses first, then alphabetically"""
        core_courses = [c for c in courses if c.get("is_core", False)]
        non_core = [c for c in courses if not c.get("is_core", False)]

        core_courses.sort(key=lambda x: x["course_title"])
        non_core.sort(key=lambda x: x["course_title"])

        return core_courses + non_core

    def _prepare_landscape_template_data(
        self,
        student_record: Dict[str, Any],
        gpa: Any,
        class_rank: Optional[Any],
        transcript_type: str,
    ) -> Dict[str, Any]:
        """Prepare data for landscape template organized by grade level"""

        # Get student ID from record
        student_id = student_record["User ID"]

        # Determine graduation year to calculate grade levels
        grad_year = student_record.get(
            "Graduation year",
            student_record.get("Grad Year", student_record.get("grad_year")),
        )

        # Get grades for this student
        student_grades_df = self.data_processor.grades[
            self.data_processor.grades["User ID"] == student_id
        ]

        # Group courses by year and course code to combine semesters
        year_course_map = {}

        for _, grade_row in student_grades_df.iterrows():
            year = grade_row["School Year"]
            course_code = str(grade_row["Course Code"])
            semester = int(grade_row["Course part number"])
            course_title = grade_row["Course Title"]

            if year not in year_course_map:
                year_course_map[year] = {}

            if course_code not in year_course_map[year]:
                # Get weight info
                weight_info = self.gpa_calculator.course_weights_index.get(course_code)

                year_course_map[year][course_code] = {
                    "course_code": course_code,
                    "course_title": course_title,
                    "school_year": year,
                    "sem1_grade": None,
                    "sem2_grade": None,
                    "weight": (
                        weight_info
                        if weight_info
                        else type(
                            "W",
                            (),
                            {
                                "credit": 0.0,
                                "weight": 0.0,
                                "is_ap": False,
                                "is_honors": False,
                            },
                        )()
                    ),
                }

            # Assign grade to appropriate semester
            if semester == 1:
                year_course_map[year][course_code]["sem1_grade"] = grade_row["Grade"]
            elif semester == 2:
                year_course_map[year][course_code]["sem2_grade"] = grade_row["Grade"]

        # Organize by grade level (9, 10, 11, 12, or middle school)
        courses_by_grade = {"9": [], "10": [], "11": [], "12": []}
        middle_school_credits = []

        # Middle school HS credit courses
        ms_hs_courses = [
            "Algebra 1",
            "Geometry",
            "Physical Science",
            "Spanish I",
            "Spanish II",
            "French I",
            "French II",
            "Latin I",
            "Latin II",
        ]

        for year in sorted(year_course_map.keys()):
            # Calculate grade level for this year
            year_parts = year.split("-")
            if len(year_parts) == 2 and grad_year:
                end_year = int(year_parts[1])
                grade_level = 12 - (grad_year - end_year)
            else:
                grade_level = 12  # default

            courses = list(year_course_map[year].values())

            if grade_level < 9:
                # Middle school - only include HS credit courses
                for course in courses:
                    course["grade_level"] = grade_level
                    course["display_year"] = year
                    if any(
                        ms_course.lower() in course["course_title"].lower()
                        for ms_course in ms_hs_courses
                    ):
                        middle_school_credits.append(course)
            else:
                # High school grades 9-12
                grade_key = str(min(grade_level, 12))  # Cap at 12
                for course in courses:
                    # Get CORE status from weight info
                    weight_info = course.get("weight")
                    course["is_core"] = getattr(weight_info, "core", False)
                    course["grade_level"] = grade_level
                    course["display_year"] = year
                    course["credits"] = getattr(weight_info, "credit", 0.0)

                courses_by_grade[grade_key].extend(courses)

        # Sort courses in each grade level (CORE first)
        for grade_key in courses_by_grade:
            courses_by_grade[grade_key] = self._sort_courses_core_first(
                courses_by_grade[grade_key]
            )

        # Sort middle school credits
        middle_school_credits = self._sort_courses_core_first(middle_school_credits)

        # School information
        school_info = {
            "school_name": "Keswick Christian School",
            "school_address": "8585 66th Street North, Pinellas Park, FL 33782",
            "school_phone": "(727) 522-5115",
            "school_website": "www.keswickchristian.org",
            "registrar_name": "School Registrar",
            "school_logo_path": str(self.assets_dir / "logos" / "text logo kcs.png"),
        }

        template_data = {
            # Student information
            "student": student_record,
            # Academic data organized by grade
            "courses_by_grade": courses_by_grade,
            "middle_school_credits": middle_school_credits,
            "gpa": gpa,
            "class_rank": class_rank,
            # Transfer credits
            "transfer_credits": [],
            # Awards (placeholder)
            "awards": [],
            # Document metadata
            "transcript_type": transcript_type,
            "issue_date": datetime.now().strftime("%B %d, %Y"),
            "verification_code": self._generate_verification_code(
                student_record["User ID"]
            ),
            # School information
            **school_info,
        }

        return template_data

    def _prepare_v2_template_data(
        self,
        student_record: Dict[str, Any],
        gpa: Any,
        class_rank: Optional[Any],
        transcript_type: str,
    ) -> Dict[str, Any]:
        """Prepare data for V2 landscape template with proper grade mapping and YTD GPAs"""

        from transcript_generator_v2 import prepare_v2_template_data

        return prepare_v2_template_data(
            student_record,
            gpa,
            class_rank,
            transcript_type,
            self.data_processor,
            self.gpa_calculator,
            self.project_root,
        )

    def _render_html(
        self, template_data: Dict[str, Any], layout: str = "landscape"
    ) -> str:
        """Render HTML from template"""

        if layout in ["minimalist", "v5", "v4", "v3"]:
            template_name = "transcript_minimalist.html"
        elif layout == "v2":
            template_name = "transcript_landscape_v2_fixed.html"
        elif layout == "landscape":
            template_name = "transcript_landscape.html"
        else:
            template_name = "transcript_template.html"

        template = self.env.get_template(template_name)
        html_content = template.render(**template_data)

        return html_content

    def _generate_pdf_weasyprint(
        self, html_content: str, output_path: Path, layout: str = "landscape"
    ):
        """Generate PDF using WeasyPrint"""

        # Select appropriate CSS based on layout
        if layout in ["minimalist", "v5", "v4", "v3"]:
            css_path = self.templates_dir / "styles_minimalist.css"
        elif layout == "v2":
            css_path = self.templates_dir / "styles_landscape_v2_fixed.css"
        elif layout == "landscape":
            css_path = self.templates_dir / "styles_landscape.css"
        else:
            css_path = self.templates_dir / "styles.css"

        # Debug: Save HTML for inspection
        debug_html_path = output_path.with_suffix(".html")
        with open(debug_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"Debug HTML saved: {debug_html_path}")

        if css_path.exists():
            css = CSS(filename=str(css_path))
            HTML(string=html_content, base_url=str(self.templates_dir)).write_pdf(
                output_path, stylesheets=[css]
            )
        else:
            logger.warning(
                f"CSS file not found: {css_path}, generating without stylesheet"
            )
            HTML(string=html_content, base_url=str(self.templates_dir)).write_pdf(
                output_path
            )

        logger.info(f"PDF generated with WeasyPrint ({layout} layout): {output_path}")

    def _generate_verification_code(self, user_id: int) -> str:
        """Generate unique verification code for transcript"""

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        code = f"KCS-{user_id}-{timestamp}"

        return code

    def generate_batch_transcripts(
        self,
        user_ids: Optional[List[int]] = None,
        graduation_year: Optional[int] = None,
        transcript_type: str = "Official",
    ) -> List[Path]:
        """
        Generate transcripts for multiple students

        Args:
            user_ids: List of specific student IDs (optional)
            graduation_year: Generate for all students in graduating class (optional)
            transcript_type: "Official" or "Unofficial"

        Returns:
            List of paths to generated PDF files
        """
        logger.info(f"🎓 Starting batch transcript generation")

        if user_ids is None and graduation_year is None:
            raise ValueError("Must specify either user_ids or graduation_year")

        # Determine which students to process
        if user_ids is None:
            # Get all students for graduation year
            user_ids = self.data_processor.get_students_by_graduation_year(
                graduation_year
            )

        logger.info(f"Processing {len(user_ids)} students")

        generated_files = []
        errors = []

        for user_id in user_ids:
            try:
                output_path = self.generate_transcript(user_id, transcript_type)
                generated_files.append(output_path)
            except Exception as e:
                logger.error(f"Error generating transcript for student {user_id}: {e}")
                errors.append((user_id, str(e)))

        logger.info(f"✅ Batch generation complete")
        logger.info(f"   Successfully generated: {len(generated_files)}")
        logger.info(f"   Errors: {len(errors)}")

        if errors:
            logger.warning("Errors encountered:")
            for user_id, error in errors:
                logger.warning(f"   Student {user_id}: {error}")

        return generated_files

    def audit_student_layout(self, user_id: int) -> Dict[str, Any]:
        """
        Calculate layout metrics for a student without generating PDF
        
        Args:
            user_id: Student ID
            
        Returns:
            Dictionary containing layout metrics (effective score, tier, risk)
        """
        # Load student data
        student_df = self.data_processor.student_details[
            self.data_processor.student_details["User ID"] == user_id
        ]
        
        if len(student_df) == 0:
            return {"error": "Student not found"}
            
        student_record = student_df.iloc[0].to_dict()
        
        # Get grades
        student_grades_df = self.data_processor.grades[
            self.data_processor.grades["User ID"] == user_id
        ]
        
        # Convert grades to objects (simplified from generate_transcript)
        from data_models import CourseGrade
        course_grades = []
        for _, row in student_grades_df.iterrows():
            try:
                # Minimal fields needed for GPA/structure
                grade = CourseGrade(
                    user_id=int(row["User ID"]),
                    first_name=row["First Name"],
                    last_name=row["Last Name"],
                    grad_year=int(row["Grad Year"]),
                    school_year=row["School Year"],
                    course_code=str(row["Course Code"]),
                    course_title=row["Course Title"],
                    course_id=(int(row["Course ID"]) if pd.notna(row.get("Course ID")) else None),
                    course_part_number=str(row["Course part number"]),
                    term_name=row["Term name"],
                    grade=str(row["Grade"]), 
                    credits_attempted=str(row.get("Credits attempted", "")),
                    credits_earned=str(row.get("Credits earned", "")),
                )
                course_grades.append(grade)
            except:
                continue
                
        # Get/Calc GPA
        if user_id in self.data_processor.gpa_results:
            gpa = self.data_processor.gpa_results[user_id]
        else:
            gpa = self.gpa_calculator.calculate_student_gpa(user_id, course_grades)
            
        # Call minimalist prep to get metrics
        from transcript_generator_minimalist import prepare_minimalist_template_data
        
        template_data = prepare_minimalist_template_data(
            student_record,
            gpa,
            self.data_processor,
            self.gpa_calculator,
            self.project_root,
        )
        
        return template_data.get("layout_metrics", {})


def main():
    """Test transcript generator with sample students"""

    print("📄 TRANSCRIPT GENERATOR TEST")
    print("=" * 60)

    # Initialize generator
    generator = TranscriptGenerator()

    # Load all data
    print("📊 Loading student data...")
    generator.data_processor.load_all_data()

    # Initialize GPA calculator
    print("🧮 Initializing GPA calculator...")
    course_weights = {}
    for _, row in generator.data_processor.gpa_weight_index.iterrows():
        course_weights[row["course_code"]] = type(
            "CourseWeight",
            (),
            {
                "credit": row["credit"],
                "weight": row["weight"],
                "core": row["CORE"] == "Yes",
                "is_ap": row["weight"] >= 1.0,
                "is_honors": row["weight"] == 0.5,
            },
        )()

    generator.gpa_calculator = GPACalculator(course_weights)

    # Calculate all GPAs and ranks
    print("🏆 Calculating class rankings...")
    student_gpas = []

    # Get sample students (top 5 from validation results)
    test_students = [5971421, 7227288, 5890209, 5606512, 4021011]

    print(f"\n📝 Generating test transcripts for {len(test_students)} students:")

    for user_id in test_students:
        try:
            print(f"\n  Generating transcript for student {user_id}...")
            output_path = generator.generate_transcript(user_id, "Official")
            print(f"  ✅ Generated: {output_path.name}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    print("\n✅ Transcript generation test complete!")
    print(f"📁 Check output/test_transcripts/ for generated files")


if __name__ == "__main__":
    main()
