#!/usr/bin/env python3
"""
Enhanced Transcript Generator V3 with Awards and Decile Rankings
- Integrated awards calculation (Principal's List, AP Scholar, ACSI, NMSQT)
- Decile-based class ranking system
- Optimized visual layout with improved spacing
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd
import base64

# Import calculation modules
from awards_calculator import calculate_all_awards, AwardResult
from decile_rank_calculator import (
    calculate_decile_ranks,
    DecileRankResult,
    get_student_decile_rank,
)

logger = logging.getLogger(__name__)

# === DUAL ENROLLMENT COURSE CODE MAPPINGS ===
DE_COURSE_CODES = {
    "Composition 1": "ENC1101",
    "Composition I": "ENC1101",
    "English Composition 1": "ENC1101",
    "Composition 2": "ENC1102",
    "Composition II": "ENC1102",
    "English Composition 2": "ENC1102",
    "US History 1": "AMH2010",
    "US History 2": "AMH2020",
    "United States History 1": "AMH2010",
    "United States History 2": "AMH2020",
    "US History": ("AMH2010", "AMH2020"),  # Generic fallback, use semester
    "United States History": ("AMH2010", "AMH2020"),  # Generic fallback, use semester
    "Intro to Literature": "LIT1000",
    "Introduction to Literature": "LIT1000",
}


def numeric_to_letter_grade(numeric_grade: float) -> str:
    """
    Convert numeric grade (0-100) to letter grade.
    Uses Keswick Christian School's grading scale.
    Returns straight letters only (no plus/minus).
    """
    if numeric_grade >= 90:
        return "A"
    elif numeric_grade >= 80:
        return "B"
    elif numeric_grade >= 70:
        return "C"
    elif numeric_grade >= 60:
        return "D"
    else:
        return "F"


def clean_course_title(
    title: str, is_ap: bool = False, is_honors: bool = False, is_de: bool = False
) -> str:
    """Remove redundant honors/AP/DE text from course titles but preserve Pre-AP"""
    cleaned = title

    # IMPORTANT: Preserve "Pre-AP" by temporarily replacing it
    pre_ap_marker = "___PREAP___"
    if "Pre-AP" in cleaned or "pre-ap" in cleaned.lower():
        # Preserve Pre-AP by marking it
        import re

        cleaned = re.sub(r"Pre-AP", pre_ap_marker, cleaned, flags=re.IGNORECASE)

    # Remove various forms of honors/AP/DE text (order matters - longer strings first)
    replacements = [
        "Dual Enrollment ",
        "dual enrollment ",
        "DUAL ENROLLMENT ",
        " Dual Enrollment",
        " dual enrollment",
        " DUAL ENROLLMENT",
        " (H)",
        "(H)",
        " (Honors)",
        "(Honors)",
        " (AP)",
        "(AP)",
        "AP ",
        "Honors ",
        "honors ",
        "H ",
        "DE ",
        " - Honors",
        " - AP",
        " Honors",
        " AP",
        " - H",
    ]

    for rep in replacements:
        cleaned = cleaned.replace(rep, "")

    # Restore Pre-AP
    cleaned = cleaned.replace(pre_ap_marker, "Pre-AP")

    # Clean up multiple spaces
    cleaned = " ".join(cleaned.split())

    return cleaned.strip()


def clean_sport_name(sport_name: str, season: str = "") -> str:
    """
    Clean sport name for transcript display.

    Handles formats like:
    - "Swimming - Varsity Boys & Girls"
    - "Track & Field - JV Boys"
    - "Basketball - Boys Varsity"

    Args:
        sport_name: Original sport name string
        season: Season (e.g., "Fall", "Winter", "Spring") - NOT USED, kept for compatibility

    Returns:
        Cleaned format like "Varsity Swimming" or "Junior Varsity Track & Field"
    """
    # Handle "Sport - Level" format
    parts = [p.strip() for p in sport_name.split("-")]
    sport_base = parts[0]
    level = ""

    if len(parts) > 1:
        level_part = parts[1].lower()
        if "varsity" in level_part and "jv" not in level_part.lower():
            level = "Varsity"
        elif "jv" in level_part or "junior varsity" in level_part:
            level = "Junior Varsity"

    base_result = f"{level} {sport_base}".strip()

    # Season is stored separately in the semester field, not in the name
    return base_result


def get_season_sort_order(season: str) -> int:
    """
    Return sort order for seasons: Fall=1, Winter=2, Spring=3, other=4
    """
    season_lower = season.lower().strip()
    if "fall" in season_lower:
        return 1
    elif "winter" in season_lower:
        return 2
    elif "spring" in season_lower:
        return 3
    else:
        return 4  # Unknown seasons go last


def calculate_diploma_designation(
    courses_by_grade: Dict, current_grade: int, grad_year: int
) -> str:
    """
    Calculate diploma designation based on completed courses.
    Shows (Projected) if student hasn't graduated yet.

    Logic:
    - Honors Diploma: 3+ years Honors+ in English OR History
    - STEM Scholars: 3+ years Honors+ in Math OR Science
    - Scholars Diploma: 3+ years Honors+ in all 4 core subjects
    - Standard Diploma: Default

    Grade-level aware:
    - Freshman (9th): look at 9th grade only
    - Sophomore (10th): look at 9th + 10th
    - Junior (11th): look at 9th + 10th + 11th
    - Senior (12th): look at all 4 years (final designation)
    """
    from datetime import datetime

    # Determine which grades to analyze based on current grade
    if current_grade == 9:
        grades_to_analyze = ["9"]
    elif current_grade == 10:
        grades_to_analyze = ["9", "10"]
    elif current_grade == 11:
        grades_to_analyze = ["9", "10", "11"]
    else:  # 12th grade
        grades_to_analyze = ["9", "10", "11", "12"]

    # Check if student has graduated (current year > grad year)
    current_year = datetime.now().year
    has_graduated = current_year > grad_year

    # Count years with Honors+ (3.5+ GPA) in each subject area
    subject_honors_years = {"english": 0, "history": 0, "math": 0, "science": 0}

    # Subject identification keywords
    subject_keywords = {
        "english": [
            "english",
            "composition",
            "literature",
            "enc1101",
            "enc1102",
            "lit1000",
        ],
        "history": ["history", "government", "civics", "amh1010", "amh1020"],
        "math": [
            "math",
            "algebra",
            "geometry",
            "calculus",
            "statistics",
            "trigonometry",
        ],
        "science": [
            "biology",
            "chemistry",
            "physics",
            "science",
            "anatomy",
            "environmental",
        ],
    }

    # Analyze each grade year
    for grade_key in grades_to_analyze:
        if grade_key not in courses_by_grade:
            continue

        # Track if this year had Honors+ in each subject
        year_honors = {subject: False for subject in subject_honors_years.keys()}

        for course in courses_by_grade[grade_key]:
            # Skip dividers and non-core courses
            if course.get("is_divider", False) or not course.get("is_core", False):
                continue

            course_title = course.get("course_title", "").lower()
            weight = course.get("weight")

            # Check if Honors+ (weight >= 0.5 indicates Honors or AP)
            is_honors_plus = False
            if weight:
                is_honors_plus = getattr(weight, "is_honors", False) or getattr(
                    weight, "is_ap", False
                )

            if not is_honors_plus:
                continue

            # Identify subject and mark as Honors+ for this year
            for subject, keywords in subject_keywords.items():
                if any(keyword in course_title for keyword in keywords):
                    year_honors[subject] = True
                    break

        # Increment year count for each subject that had Honors+ this year
        for subject, had_honors in year_honors.items():
            if had_honors:
                subject_honors_years[subject] += 1

    # Determine diploma designation
    english_years = subject_honors_years["english"]
    history_years = subject_honors_years["history"]
    math_years = subject_honors_years["math"]
    science_years = subject_honors_years["science"]

    # Scholars: 3+ years in ALL four subjects
    if all(years >= 3 for years in subject_honors_years.values()):
        designation = "Scholars Diploma"
    # STEM Scholars: 3+ years in Math OR Science
    elif math_years >= 3 or science_years >= 3:
        designation = "STEM Scholars Diploma"
    # Humanities Honors: 3+ years in English OR History
    elif english_years >= 3 or history_years >= 3:
        designation = "Humanities Honors Diploma"
    else:
        designation = "Standard Diploma"

    # Add (Projected) if not graduated
    if not has_graduated:
        designation += " (Projected)"

    return designation


def get_de_course_code(course_title: str, semester: int = 1) -> Optional[str]:
    """Get dual enrollment course code for display"""

    # First check if the course title already contains a course code
    # Format: "ASL 1140C--ASL 1" or "CLP 2140--Abnormal Psychology"
    import re

    # Look for pattern: 3-4 letters followed by space and numbers
    match = re.match(r"([A-Z]{3,4}\s*\d{4}[A-Z]?)", course_title)
    if match:
        return match.group(1).replace(" ", "")

    # Otherwise check the mapping dictionary
    for key, value in DE_COURSE_CODES.items():
        if key.lower() in course_title.lower():
            if isinstance(value, tuple):
                return value[semester - 1]  # semester 1 or 2
            return value

    return None


def calculate_ytd_gpa_for_courses(courses: List[Dict], gpa_calculator) -> float:
    """Calculate YTD weighted GPA for a specific year's courses (CORE only)"""
    if not courses:
        return 0.0

    total_points = 0.0
    total_credits = 0.0
    core_courses_counted = 0

    for course in courses:
        # CRITICAL FIX: Only count CORE courses in term GPA
        if not course.get("is_core", False):
            continue

        sem1_grade = course.get("sem1_grade")
        sem2_grade = course.get("sem2_grade")
        weight_obj = course.get("weight")

        if not weight_obj:
            continue

        credit = getattr(weight_obj, "credit", 0.0)
        weight = getattr(weight_obj, "weight", 0.0)

        course_title = course.get("course_title", "Unknown")

        for grade in [sem1_grade, sem2_grade]:
            if grade and grade != "—":
                # Handle case where grade might be float instead of string
                if isinstance(grade, (int, float)):
                    grade = str(grade)
                base_points = gpa_calculator._grade_to_points(grade)
                if base_points is not None:
                    weighted_points = base_points + weight
                    total_points += weighted_points * (credit / 2)
                    total_credits += credit / 2
                    core_courses_counted += 1
                    logger.debug(
                        f"    {course_title}: Grade={grade}, "
                        f"Base={base_points}, Weight={weight}, "
                        f"W_Pts={weighted_points}, Credit={credit/2}"
                    )

    logger.debug(
        f"  Year GPA: {core_courses_counted} core grades, "
        f"{total_credits:.1f} credits, "
        f"GPA={total_points/total_credits if total_credits > 0 else 0:.3f}"
    )
    return (total_points / total_credits) if total_credits > 0 else 0.0


def calculate_ytd_gpa_for_courses_unweighted(
    courses: List[Dict], gpa_calculator
) -> float:
    """Calculate YTD unweighted GPA for a specific year's courses (CORE only)"""
    if not courses:
        return 0.0

    total_points = 0.0
    total_credits = 0.0

    for course in courses:
        # Only CORE courses
        if not course.get("is_core", False):
            continue

        sem1_grade = course.get("sem1_grade")
        sem2_grade = course.get("sem2_grade")
        weight_obj = course.get("weight")

        if not weight_obj:
            continue

        credit = getattr(weight_obj, "credit", 0.0)

        for grade in [sem1_grade, sem2_grade]:
            if grade and grade != "—":
                # Handle case where grade might be float instead of string
                if isinstance(grade, (int, float)):
                    grade = str(grade)
                base_points = gpa_calculator._grade_to_points(grade)
                if base_points is not None:
                    # No weight added for unweighted
                    total_points += base_points * (credit / 2)
                    total_credits += credit / 2

    return (total_points / total_credits) if total_credits > 0 else 0.0


def calculate_principals_list(
    courses_by_grade: Dict, grade_metadata: Dict, gpa_calculator
) -> Dict:
    """
    Calculate Principal's List for each semester.

    Criteria:
    - CORE GPA > 4.4 for the semester, OR
    - All A's in ALL courses (including non-core)

    Returns dict: {
        'YYYY - YYYY': ['S1', 'S2'],  # Semesters that qualify
    }
    """
    principals_list = {}

    for grade_key in ["9", "10", "11", "12"]:
        if grade_key not in courses_by_grade or grade_key not in grade_metadata:
            continue

        display_year = grade_metadata[grade_key]["display_year"]
        courses = courses_by_grade[grade_key]

        logger.debug(
            f"\n=== Checking Principal's List for Grade {grade_key} ({display_year}) ==="
        )
        logger.debug(f"Total courses: {len(courses)}")

        # Check Semester 1
        logger.debug(f"\n--- Semester 1 ---")
        s1_qualifies = check_semester_principals_list(courses, 1, gpa_calculator)

        # Check Semester 2
        logger.debug(f"\n--- Semester 2 ---")
        s2_qualifies = check_semester_principals_list(courses, 2, gpa_calculator)

        semesters = []
        if s1_qualifies:
            semesters.append(1)
        if s2_qualifies:
            semesters.append(2)

        if semesters:
            principals_list[display_year] = semesters
            logger.debug(
                f"\n✅ Grade {grade_key} QUALIFIES: {', '.join([f'S{s}' for s in semesters])}"
            )
        else:
            logger.debug(f"\n❌ Grade {grade_key} does not qualify")

    return principals_list


def check_semester_principals_list(
    courses: List[Dict], semester: int, gpa_calculator
) -> bool:
    """Check if a semester qualifies for Principal's List"""
    sem_field = f"sem{semester}_grade"

    # Filter out dividers and courses without grades
    actual_courses = [
        c for c in courses if not c.get("is_divider", False) and c.get(sem_field)
    ]

    if not actual_courses:
        logger.debug(f"No actual courses for semester {semester}")
        return False

    # Check if all A's (in ALL courses)
    all_as = all(c.get(sem_field, "") in ["A", "A+"] for c in actual_courses)
    if all_as:
        logger.debug(f"All A's in semester {semester} - QUALIFIES")
        return True

    # Check if CORE GPA > 4.4
    core_courses = [c for c in actual_courses if c.get("weight") and c["weight"].core]
    if not core_courses:
        logger.debug(f"No core courses for semester {semester}")
        return False

    total_points = 0.0
    total_credits = 0.0

    for course in core_courses:
        grade = course.get(sem_field, "")
        if not grade or grade == "—":
            continue

        weight_obj = course.get("weight")
        if not weight_obj:
            continue

        # Calculate weighted GPA points for this grade
        base_points = gpa_calculator._grade_to_points(grade)
        if base_points is None:
            continue

        weight = getattr(weight_obj, "weight", 0.0)
        weighted_points = base_points + weight

        # 0.5 credits per semester
        total_points += weighted_points * 0.5
        total_credits += 0.5

        logger.debug(
            f"  Course: {course.get('title', 'Unknown')}, "
            f"Grade: {grade}, Base: {base_points}, Weight: {weight}, "
            f"Weighted: {weighted_points}"
        )

    core_gpa = (total_points / total_credits) if total_credits > 0 else 0.0
    qualifies = core_gpa > 4.4

    logger.debug(
        f"Semester {semester} Core GPA: {core_gpa:.3f} "
        f"(Points: {total_points}, Credits: {total_credits}) - "
        f"{'QUALIFIES' if qualifies else 'DOES NOT QUALIFY'}"
    )

    return qualifies


def prepare_minimalist_template_data(
    student_record: Dict[str, Any],
    gpa: Any,
    data_processor,
    gpa_calculator,
    project_root: Path,
) -> Dict[str, Any]:
    """
    Prepare data for V3 landscape template with:
    - Decile-based class ranking
    - Comprehensive awards calculation
    - Optimized layout data
    """

    student_id = student_record["User ID"]
    grad_year = int(
        student_record.get("Graduation year", student_record.get("Grad Year", 2025))
    )

    # Parse grade level (could be "11th Grade" or just "11")
    grade_level_str = str(student_record.get("Student grade level", "12"))
    if (
        "th" in grade_level_str
        or "st" in grade_level_str
        or "nd" in grade_level_str
        or "rd" in grade_level_str
    ):
        import re

        match = re.search(r"(\d+)", grade_level_str)
        current_grade = int(match.group(1)) if match else 12
    else:
        current_grade = int(grade_level_str) if grade_level_str.isdigit() else 12

    current_year = datetime.now().year

    # Add formatted current grade level to student record
    grade_suffix = {1: "st", 2: "nd", 3: "rd"}.get(
        current_grade if current_grade <= 3 else 0, "th"
    )
    student_record["current_grade_level"] = f"{current_grade}{grade_suffix} Grade"

    logger.info(
        f"Processing student {student_id}, grad year {grad_year}, grade {current_grade}"
    )

    # Get all grades for this student
    # Get all grades for this student (School + Transfer)
    student_school_grades = data_processor.grades[
        data_processor.grades["User ID"] == student_id
    ]
    
    student_transfer_grades = data_processor.transfer_grades[
        data_processor.transfer_grades["User ID"].astype(str) == str(student_id)
    ]
    
    # Mark transfer rows for distinct processing in main loop
    if not student_transfer_grades.empty:
        student_transfer_grades = student_transfer_grades.copy()
        student_transfer_grades["is_transfer_row"] = True
    
    # Merge them
    student_grades_df = pd.concat([student_school_grades, student_transfer_grades], ignore_index=True)


    # === CALCULATE CLASS RANK ===
    # Get all students in the same graduation year
    same_grad_students = data_processor.student_details[
        data_processor.student_details["Graduation year"] == grad_year
    ]

    # Get GPA data from pre-calculated results (only full-time students)
    student_gpa_data = []
    for _, peer in same_grad_students.iterrows():
        peer_id = peer["User ID"]

        # Get pre-calculated GPA (only exists for full-time students)
        peer_gpa_record = data_processor.gpa_results.get(peer_id)
        if peer_gpa_record:
            # Get course count for this student
            peer_grades = data_processor.grades[
                data_processor.grades["User ID"] == peer_id
            ]
            unique_courses = peer_grades["Course Code"].nunique()

            core_weighted = peer_gpa_record.core_weighted_gpa
            student_gpa_data.append((peer_id, core_weighted, unique_courses))

    logger.info(
        f"Class rank data: {len(student_gpa_data)} students in grad year {grad_year}"
    )

    # Calculate decile rankings
    decile_rankings = calculate_decile_ranks(student_gpa_data, grad_year)
    class_rank = get_student_decile_rank(student_id, decile_rankings)

    # Manual override for Grant Cook (4021011) - foreign language penalty
    if student_id == 4021011:
        class_rank = DecileRankResult(
            user_id=4021011,
            rank=class_rank.rank,
            total_students=class_rank.total_students,
            decile="1st Decile",
            percentile=class_rank.percentile,
            core_weighted_gpa=class_rank.core_weighted_gpa,
            is_part_time=False,
        )

    # === CALCULATE AWARDS ===
    # Convert grades dataframe to list of dicts
    student_grades_list = []
    for _, row in student_grades_df.iterrows():
        course_code = str(row["Course Code"])
        weight_info = gpa_calculator.course_weights_index.get(course_code)

        # Handle semester (Transfer grades may lack this column)
        raw_sem = row.get("Course part number")
        try:
            semester = int(raw_sem) if pd.notna(raw_sem) else 1
        except (ValueError, TypeError):
            semester = 1

        grade_dict = {
            "school_year": row["School Year"],
            "semester": semester,
            "course_code": course_code,
            "course_title": row["Course Title"],
            "grade": row["Grade"],
            "is_core": getattr(weight_info, "core", False) if weight_info else False,
            "weight": getattr(weight_info, "weight", 0.0) if weight_info else 0.0,
            "is_ap": getattr(weight_info, "is_ap", False) if weight_info else False,
        }
        student_grades_list.append(grade_dict)

    # === LOAD TEST SCORES (SAT SUPERSCORE) ===
    test_scores = {}
    sat_data = data_processor.get_sat_superscore_for_student(student_id)
    if sat_data:
        test_scores["sat"] = {
            "total": sat_data["total"],
            "erw": sat_data["ebrw"],
            "math": sat_data["math"],
            "attempts": sat_data["num_attempts"],
        }
        logger.info(
            f"  📊 SAT data loaded: Total={sat_data['total']}, EBRW={sat_data['ebrw']}, Math={sat_data['math']}"
        )
    else:
        logger.info(f"  📊 No SAT data found for student {student_id}")

    # === EXTRACT AP SCORES (FROM AP DATAFILE) ===
    ap_data = data_processor.get_ap_scores_for_student(
        student_record["First name"], student_record["Last name"]
    )
    ap_scores = ap_data["exams"] if ap_data else []
    ap_awards = ap_data["awards"] if ap_data else []

    # Calculate total college credits earned from AP
    # Rules per user specification:
    # - US History (1/2), European History, Eng Lang, Eng Lit:
    #   6 credits (scores 4-5)
    # - Biology: 4 credits (score 4) or 8 credits (score 5)
    # - All other exams: 3 credits per exam (scores 3-5)
    ap_college_credits = 0
    for exam in ap_scores:
        score = exam["score"]
        subject = exam["subject"]

        if score >= 3:  # Qualifying score
            # Check for 6-credit exams
            six_credit_exams = [
                "US History",
                "U.S. History",
                "United States History",
                "European History",
                "English Language",
                "English Lit",
            ]
            if any(x in subject for x in six_credit_exams):
                if score >= 4:
                    exam_credits = 6
                else:
                    exam_credits = 3  # Score of 3 gets standard 3 credits
            # Check for Biology special case
            elif "Biology" in subject:
                if score == 5:
                    exam_credits = 8
                elif score == 4:
                    exam_credits = 4
                else:
                    exam_credits = 3  # Score of 3 gets standard 3 credits
            # All other exams
            else:
                exam_credits = 3

            ap_college_credits += exam_credits

    # === LOAD SPORTS PARTICIPATION ===
    sports_list = data_processor.get_sports_for_student(
        student_record["First name"], student_record["Last name"], grad_year
    )

    # === LOAD COURSES IN PROGRESS ===
    courses_in_progress = data_processor.get_courses_in_progress_for_student(student_id)
    logger.info(
        f"  📝 Courses in progress count: {len(courses_in_progress) if courses_in_progress else 0}"
    )
    if courses_in_progress:
        logger.info(
            f"  📝 Sample courses: {[c.get('title') for c in courses_in_progress[:3]]}"
        )

    # === LOAD AWARDS FROM CSV ===
    # NOTE: We only use Sports from CSV for distinctions
    # Principal's List is calculated separately
    # All other awards (Honor Roll, etc.) are NOT shown in distinctions
    awards = []
    awards_by_year = {}

    # We don't load any awards from CSV - only calculated Principal's List and Sports will show

    # === MERGE SPORTS INTO AWARDS BY YEAR ===
    # Convert sports participation into award-like objects for distinctions
    logger.info(f"  📊 Processing {len(sports_list)} sports participations")
    for sport in sports_list:
        # Create a synthetic award for the sport
        sport_year = sport.get("year", "")
        if sport_year:
            # Normalize year format to match awards "YYYY - YYYY" (spaces)
            year_normalized = (
                sport_year.replace("-", " - ")
                if " - " not in sport_year
                else sport_year
            )

            # Clean up sport name (e.g., "Swimming - Varsity Boys & Girls" + "Fall" -> "Varsity Swimming (Fall)")
            season = sport.get("season", "")
            clean_name = clean_sport_name(sport.get("sport", ""), season)

            # Create an AwardResult object for the sport
            sport_award = AwardResult(
                award_name=clean_name,
                award_type="athletic",
                year_earned=year_normalized,
                semester=season,
                details=None,
            )

            # Add to awards_by_year
            if year_normalized not in awards_by_year:
                awards_by_year[year_normalized] = []
            awards_by_year[year_normalized].append(sport_award)
            logger.info(f"     Added sport: {clean_name} to year {year_normalized}")

    # Sort sports within each year by season (Fall, Winter, Spring)
    for year in awards_by_year:
        # Separate athletic awards from other awards
        athletic_awards = [
            a for a in awards_by_year[year] if a.award_type == "athletic"
        ]
        other_awards = [a for a in awards_by_year[year] if a.award_type != "athletic"]

        # Sort athletic awards by season
        athletic_awards.sort(key=lambda a: get_season_sort_order(a.semester or ""))

        # Combine back: other awards first, then sorted athletic awards
        awards_by_year[year] = other_awards + athletic_awards

    logger.info(f"  📊 Total awards_by_year keys: {list(awards_by_year.keys())}")

    # === CATEGORIZE MAJOR RECOGNITIONS FOR FINAL PAGE ===
    major_recognitions = {
        "valedictorian": False,
        "salutatorian": False,
        "class_marshal": False,
        "ap_scholar_awards": [],
        "nmsqt_awards": [],
        "diploma_distinction": "Keswick Standard Diploma",  # Default for all graduates
    }

    for award in awards:
        if "Valedictorian" in award.award_name:
            major_recognitions["valedictorian"] = True
        elif "Salutatorian" in award.award_name:
            major_recognitions["salutatorian"] = True
        elif "Marshal" in award.award_name or "Marshall" in award.award_name:
            major_recognitions["class_marshal"] = True
        elif "AP Scholar" in award.award_name or "AP Capstone" in award.award_name:
            major_recognitions["ap_scholar_awards"].append(award)
        elif "NMSQT" in award.award_name or "National Merit" in award.award_name:
            major_recognitions["nmsqt_awards"].append(award)

    # TODO: Calculate diploma distinction based on course history
    # For now, keep default as Standard Diploma
    # Future: Check for Scholars, STEM Honors, Humanities Honors criteria

    # === ORGANIZE COURSES BY GRADE ===
    year_course_map = {}

    for _, row in student_grades_df.iterrows():
        school_year = row["School Year"]
        
        # Normalize course code (handle .0 suffixes from IDs/Pandas)
        raw_code = str(row["Course Code"])
        if raw_code.endswith(".0"):
            course_code = raw_code[:-2]
        else:
            course_code = raw_code

        # Handle semester (Transfer grades may lack this column)
        raw_sem = row.get("Course part number")
        try:
            semester = int(raw_sem) if pd.notna(raw_sem) else 1
        except (ValueError, TypeError):
            semester = 1

        # Explicit check - handle NaN/None
        is_transfer_row = row.get("is_transfer_row") == True
        if not is_transfer_row:
            if school_year not in year_course_map:
                year_course_map[school_year] = {}

            if course_code not in year_course_map[school_year]:
                weight_info = gpa_calculator.course_weights_index.get(course_code)
                
                # Detect honors from title logic (regex results)
                # Detect honors from title logic (regex results)
                # Handle NaN/None safely - only True is True
                val = row.get("Is Honors Detected")
                is_honors_detected = True if val is True or val == 1.0 else False
                
                if not weight_info:
                    weight_info = type(
                        "W",
                        (),
                        {
                            "credit": 1.0,
                            "weight": 0.0,
                            "is_ap": False,
                            "is_honors": False,
                            "core": False,
                        },
                    )()
                
                # FORCE HONORS IN WEIGHT IF DETECTED
                if is_honors_detected and not getattr(weight_info, "is_honors", False) and not getattr(weight_info, "is_ap", False):
                    # Create a modified clone of the weight info
                    # If it's a Pydantic model (CourseWeight), use copy approach
                    # If it's a dynamic object (W), create new one
                    old_weight = getattr(weight_info, "weight", 0.0)
                    # If weight is standard/unweighted (e.g. 0.0 or 4.0 scale base?), add 0.5
                    # Assuming 0.0 in index means "standard". If it has a value, we add 0.5.
                    # Simplification: If it was 0.0, make it 0.5. If it was X, make it X+0.5?
                    # Actually, CourseWeight in data_models has weight. 
                    # Let's just set it to 0.5 as a safe default for "Honors" if it was 0.
                    if old_weight == 0.0: 
                        new_val = 0.5 
                    else: 
                        new_val = old_weight # If it already has weight, maybe keep it? Or add 0.5?
                        # Safe bet: Honors usually 0.5.
                    
                    # We need an object that behaves like weight_info but with is_honors=True
                    # We can use a simple class
                    class HonorsWeightOverlay:
                        def __init__(self, original, new_weight):
                            self.original = original
                            self.weight = new_weight
                            self.is_honors = True
                            self.is_ap = getattr(original, "is_ap", False)
                            self.core = getattr(original, "core", False)
                            self.credit = getattr(original, "credit", 1.0)
                            
                    weight_info = HonorsWeightOverlay(weight_info, new_val)

                course_title = row["Course Title"]
                # Detect DE courses
                is_de = "dual enrollment" in course_title.lower() or "DE " in course_title
                de_code_sem1 = get_de_course_code(course_title, 1) if is_de else None
                de_code_sem2 = get_de_course_code(course_title, 2) if is_de else None

                # For Pre-AP courses, don't clean - "Pre-AP" is part of the official name
                if "Pre-AP" in course_title or "pre-ap" in course_title.lower():
                    cleaned_title_keswick = course_title
                else:
                    cleaned_title_keswick = clean_course_title(
                        course_title,
                        getattr(weight_info, "is_ap", False),
                        getattr(weight_info, "is_honors", False) or is_honors_detected,
                        is_de,
                    )

                year_course_map[school_year][course_code] = {
                    "course_code": course_code,
                    "course_title": course_title,
                    "cleaned_title": cleaned_title_keswick,
                    "school_year": school_year,
                    "sem1_grade": None,
                    "sem2_grade": None,
                    "weight": weight_info,
                    "is_core": getattr(weight_info, "core", False),
                    "is_de": is_de,
                    "is_honors_detected": is_honors_detected,
                    "de_code_sem1": de_code_sem1,
                    "de_code_sem2": de_code_sem2,
                }


            # Clean grade: If numeric (e.g. transfer), convert to letter
            # This handles cases where transfer grades come in as "90", "85", etc.
            raw_grade = str(row["Grade"]).strip()
            final_grade = raw_grade
            
            if raw_grade.replace('.', '', 1).isdigit():
                 try:
                     val = float(raw_grade)
                     if val > 5.0: # Heuristic: GPA points are <= 5. Grades like 90/85 are percentages.
                          final_grade = numeric_to_letter_grade(val)
                 except ValueError:
                     pass

            if semester == 1:
                year_course_map[school_year][course_code]["sem1_grade"] = final_grade
            elif semester == 2:
                year_course_map[school_year][course_code]["sem2_grade"] = final_grade

    # Map courses to grade levels
    courses_by_grade = {}
    middle_school_credits = []
    year_gpas = {}

    ms_hs_keywords = [
        "algebra",
        "alg ",
        "alg.",
        "geometry",
        "geo ",
        "physical science",
        "spanish",
        "french",
        "latin",
        "biology",
        "bio ",
        "chemistry",
        "chem ",
        "physics",
        "pre-calculus",
        "calculus",
    ]

    for school_year in sorted(year_course_map.keys()):
        year_parts = school_year.replace(" ", "").split("-")
        if len(year_parts) == 2:
            end_year = int(year_parts[1])
        else:
            import re

            years = re.findall(r"\d{4}", school_year)
            end_year = int(years[-1]) if years else current_year

        grade_level = 12 - (grad_year - end_year)
        courses = list(year_course_map[school_year].values())

        for course in courses:
            course["display_year"] = school_year
            course["grade_level"] = grade_level

            # Calculate credits: F grade = 0 credits for that semester
            # Default is 1.0 credits per year (0.5 per semester)
            full_credit = getattr(course.get("weight"), "credit", 1.0)
            sem1_grade = course.get("sem1_grade")
            sem2_grade = course.get("sem2_grade")

            # Start with full year credit
            earned_credit = full_credit

            # Deduct half credit (0.5) for each F grade
            if sem1_grade == "F":
                earned_credit -= full_credit / 2
            if sem2_grade == "F":
                earned_credit -= full_credit / 2

            course["credits"] = earned_credit

        if grade_level < 9:
            ms_honors_keywords = [
                "algebra",
                "alg ", # Catch "Alg 1"
                "alg.", # Catch "Alg. 1"
                "geometry",
                "biology",
                "chemistry",
                "physics",
                "physical science",
                "pre-calculus",
                "calculus"
            ]
            
            for course in courses:
                course_lower = course["course_title"].lower()
                if any(keyword in course_lower for keyword in ms_hs_keywords):
                    # Format grade_level with ordinal suffix for display
                    suffix_map = {1: "st", 2: "nd", 3: "rd"}
                    suffix = suffix_map.get(grade_level, "th")
                    course["grade_level"] = f"{grade_level}{suffix}"
                    
                    # MS HONORS OVERRIDE: Math/Science taken early is Honors
                    has_honors_weight = getattr(weight_info, "is_honors", False)
                    keyword_match = any(hk in course_lower for hk in ms_honors_keywords)
                    
                    if keyword_match and not has_honors_weight and not getattr(weight_info, "is_ap", False):

                            # Force Honors Override
                            # Define overlay class (copied from above loop to ensure scope availability)
                            class HonorsWeightOverlay:
                                def __init__(self, original, new_weight):
                                    self.original = original
                                    self.weight = new_weight
                                    self.is_honors = True
                                    self.is_ap = getattr(original, "is_ap", False)
                                    self.core = getattr(original, "core", False)
                                    self.credit = getattr(original, "credit", 1.0)
                            
                            old_weight = getattr(weight_info, "weight", 0.0)
                            new_val = 0.5 if old_weight == 0.0 else old_weight 
                            
                            course["weight"] = HonorsWeightOverlay(weight_info, new_val)
                            course["is_honors_detected"] = True
                            has_honors_weight = True # Now it is honors

                    # Force title update if it is honors (either originally or overridden)
                    # This ensures the template badge logic works even if template ignores weight object
                    if has_honors_weight:
                         if "(H)" not in course["course_title"] and "Honors" not in course["course_title"] and "<span" not in course["course_title"]:
                                course["course_title"] = f"{course['course_title']} (H)"
                    
                    middle_school_credits.append(course)
        elif 9 <= grade_level <= 12:
            grade_key = str(grade_level)
            if grade_key not in courses_by_grade:
                courses_by_grade[grade_key] = []

            courses_by_grade[grade_key].extend(courses)

            try:
                ytd_gpa = calculate_ytd_gpa_for_courses(courses, gpa_calculator)
                ytd_gpa_uw = calculate_ytd_gpa_for_courses_unweighted(
                    courses, gpa_calculator
                )
                year_gpas[grade_key] = ytd_gpa
                year_gpas[f"{grade_key}_uw"] = ytd_gpa_uw
            except Exception as e:
                logger.warning(
                    f"Could not calculate YTD GPA for grade {grade_key}: {e}"
                )
                year_gpas[grade_key] = 0.0

    # Deduplicate courses by cleaned title (merging Transfer + School records)
    def consolidate_duplicate_courses(courses_list):
        consolidated = {}
        for course in courses_list:
            # Determine if this row is a transfer row (from legacy format)
            # Use cleaned title as key for robust matching
            key = course.get("cleaned_title", course["course_title"].strip())
            
            if key in consolidated:
                existing = consolidated[key]
                # Merge grades
                if not existing.get("sem1_grade") and course.get("sem1_grade"):
                    existing["sem1_grade"] = course["sem1_grade"]
                    # If we merged a numeric grade, convert it if needed
                    # logic handled in main loop but good to ensure
                if not existing.get("sem2_grade") and course.get("sem2_grade"):
                    existing["sem2_grade"] = course["sem2_grade"]
                
                # Merge credits
                existing["credits"] = max(existing.get("credits", 0), course.get("credits", 0))
                
                # Merge checks
                if course.get("is_honors_detected"): existing["is_honors_detected"] = True
                
                # Prefer the entry with valid weight info if current lacks it?
                # Usually school entry has better weight info.
                w_ex = existing.get("weight")
                w_new = course.get("weight")
                if w_new and (not w_ex or getattr(w_ex, "weight", 0) == 0):
                    existing["weight"] = w_new
                    
            else:
                consolidated[key] = course
        return list(consolidated.values())

    # Sort courses by CORE status and level (AP → DE → Honors → Regular)
    def sort_courses_by_priority(courses_list):
        """Sort courses by CORE status and level priority
        Order: CORE (AP → DE → Honors → Regular), then Non-CORE (same order)
        """

        def get_sort_key(course):
            is_core = course.get("is_core", False)
            weight = course.get("weight")

            # Determine level (4=AP, 3=DE, 2=Honors, 1=Regular)
            if getattr(weight, "is_ap", False):
                level = 4
            elif course.get("is_de", False):
                level = 3
            elif getattr(weight, "is_honors", False) or course.get("is_honors_detected", False):
                level = 2
            else:
                level = 1

            # CORE courses first (0), then non-CORE (1)
            core_priority = 0 if is_core else 1

            # Sort: (CORE status, -level, course_title)
            # Negative level to get descending order (AP first, Regular last)
            return (core_priority, -level, course.get("course_title", ""))

        return sorted(courses_list, key=get_sort_key)

    # Apply consolidation and sorting to all grade levels
    for grade_key in courses_by_grade:
        # Consolidate first
        courses_by_grade[grade_key] = consolidate_duplicate_courses(courses_by_grade[grade_key])
        # Then sort
        courses_by_grade[grade_key] = sort_courses_by_priority(courses_by_grade[grade_key])
        
        try:
            # Recalculate gpa for the consolidated list??
            # ytd_gpa functions use the list.
            pass
        except: pass

    middle_school_credits = consolidate_duplicate_courses(middle_school_credits)
    middle_school_credits = sort_courses_by_priority(middle_school_credits)


    middle_school_credits = sort_courses_by_priority(middle_school_credits)

    # === INTEGRATE TRANSFER CREDITS INTO GRADE BLOCKS ===
    if hasattr(data_processor, "transfer_grades"):
        student_transfers = data_processor.transfer_grades[
            data_processor.transfer_grades["User ID"] == student_id
        ]

        # Group transfers by grade -> school -> courses
        transfer_by_year_school = {}
        transfer_middle_school = []  # NEW: Track middle school transfer credits

        for _, row in student_transfers.iterrows():
            school_year = row.get("School Year", "")
            source_school = row.get(
                "Transfer School Name", row.get("Source School", "Transfer Institution")
            )
            course_title = row["Course Title"]

            # Calculate grade level for this transfer
            year_parts = school_year.replace(" ", "").split("-")
            if len(year_parts) == 2:
                end_year = int(year_parts[1])
            else:
                import re

                years = re.findall(r"\d{4}", school_year)
                end_year = int(years[-1]) if years else current_year

            grade_level = 12 - (grad_year - end_year)

            # Handle middle school transfer credits (Algebra 1, Geometry, etc. from grade < 9)
            # DISABLED: We now merge transfer grades directly into main flow via pd.concat
            # if grade_level < 9:
            #    course_lower = course_title.lower()
            #    # Check if this is a high school level course taken in middle school
            #    if any(keyword in course_lower for keyword in ms_hs_keywords):
            #         ... logic removed to prevent duplicates ...
            #        pass

                    # if existing:
                    #     # Add second semester grade
                    #     if not existing["sem2_grade"]:
                    #         existing["sem2_grade"] = letter_grade
                    #         existing["credits"] += credits_earned
                    # else:
                    #     # Create new middle school transfer course entry
                    #     suffix_map = {1: "st", 2: "nd", 3: "rd"}
                    #     suffix = suffix_map.get(grade_level, "th")
                    #
                    #     # For Pre-AP courses, don't clean - keep the full title
                    #     if "Pre-AP" in course_title or "pre-ap" in course_title.lower():
                    #         cleaned_ms_title = course_title
                    #     else:
                    #         cleaned_ms_title = clean_course_title(
                    #             course_title, False, False, False
                    #         )
                    #
                    #     transfer_middle_school.append(
                    #         {
                    #             "course_code": str(row.get("Course Code", "")),
                    #             "course_title": course_title,
                    #             "cleaned_title": cleaned_ms_title,
                    #             "school_year": school_year,
                    #             "sem1_grade": letter_grade,
                    #             "sem2_grade": None,
                    #             "weight": weight_info,
                    #             "is_core": getattr(weight_info, "core", False),
                    #             "display_year": school_year,
                    #             "grade_level": f"{grade_level}{suffix}",
                    #             "is_transfer": True,
                    #             "source_school": source_school,
                    #             "is_de": False,
                    #             "de_code_sem1": None,
                    #             "de_code_sem2": None,
                    #             "credits": credits_earned,
                    #         }
                    #     )
                # continue  # Skip to next transfer grade

            if is_transfer_row:
                source_school = row.get("School Name", "Transfer")
                if 9 <= grade_level <= 12:
                    grade_key = str(grade_level)

                    if grade_key not in transfer_by_year_school:
                        transfer_by_year_school[grade_key] = {}

                    if source_school not in transfer_by_year_school[grade_key]:
                        transfer_by_year_school[grade_key][source_school] = {}

                    # Group by course to consolidate semesters
                    if (
                        course_title
                        not in transfer_by_year_school[grade_key][source_school]
                    ):
                        weight_info = gpa_calculator.course_weights_index.get(
                            str(row.get("Course Code", ""))
                        )
                        if not weight_info:
                            weight_info = type(
                                "W",
                                (),
                                {
                                    "credit": 1.0,
                                    "weight": 0.0,
                                    "is_ap": False,
                                    "is_honors": False,
                                    "core": False,
                                },
                            )()

                        # Detect DE in transfer courses
                        # Check for: "dual enrollment", "DE ", or college course codes
                        is_de = (
                            "dual enrollment" in course_title.lower()
                            or "DE " in course_title
                            or any(
                                prefix in course_title
                                for prefix in [
                                    "ENC",
                                    "AMH",
                                    "PSY",
                                    "ASL",
                                    "CLP",
                                    "MAC",
                                    "CHM",
                                    "PHY",
                                    "BIO",
                                    "SPN",
                                    "FRE",
                                    "LIT",
                                    "HUM",
                                    "PHI",
                                ]
                            )
                        )
                        de_code_sem1 = (
                            get_de_course_code(course_title, 1) if is_de else None
                        )
                        de_code_sem2 = (
                            get_de_course_code(course_title, 2) if is_de else None
                        )

                        # For Pre-AP courses, don't clean the title - "Pre-AP" is part of the official name
                        if "Pre-AP" in course_title or "pre-ap" in course_title.lower():
                            cleaned_title_to_use = course_title
                        else:
                            cleaned_title_to_use = clean_course_title(
                                course_title,
                                getattr(weight_info, "is_ap", False),
                                getattr(weight_info, "is_honors", False),
                                is_de,
                            )

                        transfer_by_year_school[grade_key][source_school][course_title] = {
                            "course_code": str(row.get("Course Code", "")),
                            "course_title": course_title,
                            "cleaned_title": cleaned_title_to_use,
                            "school_year": school_year,
                            "sem1_grade": None,
                            "sem2_grade": None,
                            "weight": weight_info,
                            "is_core": getattr(weight_info, "core", False),
                            "display_year": school_year,
                            "grade_level": grade_level,
                            "is_transfer": True,
                            "source_school": source_school,
                            "is_de": is_de,
                            "de_code_sem1": de_code_sem1,
                            "de_code_sem2": de_code_sem2,
                            "credits": 0.0,
                            "_semester_count": 0,  # Track which semester this is
                        }

                    # Add semester grades (transfer grades don't have semester column, so count occurrences)
                    grade_value = row.get("Grade", "")

                    # Convert numerical grade to letter grade if it's a number
                    if grade_value and str(grade_value).replace(".", "", 1).isdigit():
                        try:
                            numeric_grade = float(grade_value)
                            letter_grade = numeric_to_letter_grade(numeric_grade)
                        except (ValueError, TypeError):
                            letter_grade = str(grade_value)
                    else:
                        letter_grade = str(grade_value) if grade_value else ""

                    # F grade = 0 credits, otherwise use Credits Attempted or default 0.5
                    if letter_grade == "F":
                        credits_earned = 0.0
                    else:
                        credits_earned = float(row.get("Credits Attempted", 0.5))

                    course_entry = transfer_by_year_school[grade_key][source_school][
                        course_title
                    ]
                    course_entry["_semester_count"] += 1

                    if course_entry["_semester_count"] == 1:
                        course_entry["sem1_grade"] = letter_grade
                    elif course_entry["_semester_count"] == 2:
                        course_entry["sem2_grade"] = letter_grade

                    course_entry["credits"] += credits_earned
                    
                elif grade_level < 9:
                    # Middle School Transfer - add to middle_school_credits
                    course_lower = course_title.lower()
                    
                    # Check if this is a HS-level course taken in MS (Algebra, Geometry, etc.)
                    if any(keyword in course_lower for keyword in ms_hs_keywords):
                        # Convert numeric grade to letter
                        raw_grade = row.get("Grade", "")
                        try:
                            if str(raw_grade).replace(".", "", 1).isdigit():
                                letter_grade = numeric_to_letter_grade(float(raw_grade))
                            else:
                                letter_grade = str(raw_grade) if pd.notna(raw_grade) else ""
                        except ValueError:
                            letter_grade = str(raw_grade) if pd.notna(raw_grade) else ""
                        
                        # Calculate credit
                        try:
                            credit = float(row.get("Credits Attempted", 0.5))
                        except (ValueError, TypeError):
                            credit = 0.5
                        
                        if letter_grade == "F":
                            credit = 0.0
                        
                        # Define keywords locally (same as in school grades block)
                        ms_honors_keywords_local = [
                            "algebra", "alg ", "alg.", "geometry", "geo ", 
                            "physical science", "spanish", "french", "latin",
                            "biology", "bio ", "chemistry", "chem ", "physics",
                            "pre-calculus", "calculus"
                        ]
                        
                        # Check honors based on title keywords
                        is_honors_detected = any(hk in course_lower for hk in ms_honors_keywords_local)
                        
                        # Grade level suffix
                        suffix_map = {1: "st", 2: "nd", 3: "rd"}
                        suffix = suffix_map.get(grade_level, "th")
                        
                        # Clean title
                        if "Pre-AP" in course_title or "pre-ap" in course_lower:
                            cleaned_title = course_title
                        else:
                            cleaned_title = clean_course_title(course_title, False, is_honors_detected, False)
                        
                        # Check if course already exists (consolidate semesters)
                        existing = next((c for c in middle_school_credits 
                                        if c.get("course_title") == course_title 
                                        and c.get("is_transfer")), None)
                        
                        if existing:
                            if not existing.get("sem2_grade"):
                                existing["sem2_grade"] = letter_grade
                                existing["credits"] = existing.get("credits", 0) + credit
                        else:
                            # Create dummy weight object for template compatibility
                            weight_obj = type("W", (), {
                                "credit": credit,
                                "weight": 0.5 if is_honors_detected else 0.0,
                                "is_ap": False,
                                "is_honors": is_honors_detected,
                                "core": True,
                            })()
                            
                            middle_school_credits.append({
                                "course_code": str(row.get("Course Code", "")),
                                "course_title": course_title,
                                "cleaned_title": cleaned_title,
                                "school_year": school_year,
                                "sem1_grade": letter_grade,
                                "sem2_grade": "",
                                "credits": credit,
                                "grade_level": f"{grade_level}{suffix}",
                                "is_honors_detected": is_honors_detected,
                                "is_transfer": True,
                                "weight": weight_obj,
                                "source_school": source_school,
                            })

    # Integrate transfer courses into courses_by_grade with dividers
    for grade_key in transfer_by_year_school:
        if grade_key not in courses_by_grade:
            courses_by_grade[grade_key] = []

        # Separate KCS and transfer courses
        kcs_courses = [
            c
            for c in courses_by_grade[grade_key]
            if not c.get("is_transfer", False)
        ]

        # Build integrated list with school groupings
        integrated_courses = []

        # Add KCS courses first (if any)
        if kcs_courses:
            integrated_courses.extend(kcs_courses)

        # Add transfer courses grouped by school
        for source_school, courses_dict in transfer_by_year_school[
            grade_key
        ].items():
            # Add divider
            integrated_courses.append(
                {
                    "is_divider": True,
                    "divider_text": f"Transfer from {source_school}",
                    "source_school": source_school,
                }
            )

            # Add courses from this school
            school_courses = list(courses_dict.values())
            integrated_courses.extend(sort_courses_by_priority(school_courses))

        courses_by_grade[grade_key] = integrated_courses

    # Add transfer middle school credits to main middle school list
    if transfer_middle_school:
        middle_school_credits.extend(transfer_middle_school)
        # Re-sort after adding transfer credits
        middle_school_credits = sort_courses_by_priority(middle_school_credits)

    # === RECALCULATE YEAR GPAs TO INCLUDE TRANSFER COURSES ===
    # Critical fix: year_gpas was calculated from regular courses only
    # Now recalculate using combined regular + transfer courses
    for grade_key in ["9", "10", "11", "12"]:
        if grade_key in courses_by_grade:
            # Filter out divider entries
            actual_courses = [
                c for c in courses_by_grade[grade_key] if not c.get("is_divider", False)
            ]
            if actual_courses:
                # DEBUG: Print what courses are being used for GPA calculation
                if grade_key == "9":
                    logger.info("\n🔍 DEBUG: Grade 9 courses for GPA calculation:")
                    for idx, c in enumerate(actual_courses):
                        title = (
                            c.get("course_title")
                            if c.get("course_title") is not None
                            else "NULL_TITLE"
                        )
                        is_core = c.get("is_core", False)
                        s1 = c.get("sem1_grade")
                        s2 = c.get("sem2_grade")
                        logger.info(
                            f"  [{idx}] {title:<45} is_core={is_core} "
                            f"S1={repr(s1)} S2={repr(s2)}"
                        )

                try:
                    ytd_gpa = calculate_ytd_gpa_for_courses(
                        actual_courses, gpa_calculator
                    )
                    ytd_gpa_uw = calculate_ytd_gpa_for_courses_unweighted(
                        actual_courses, gpa_calculator
                    )
                    year_gpas[grade_key] = ytd_gpa
                    year_gpas[f"{grade_key}_uw"] = ytd_gpa_uw
                    logger.info(
                        f"  ✅ Recalculated Grade {grade_key} GPA with transfers: W={ytd_gpa:.3f}, UW={ytd_gpa_uw:.3f}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not recalculate YTD GPA for grade {grade_key}: {e}"
                    )

    # === CREATE GRADE METADATA (year, gpa) FOR HEADERS ===
    grade_metadata = {}
    for grade_key in ["9", "10", "11", "12"]:
        if grade_key in courses_by_grade and len(courses_by_grade[grade_key]) > 0:
            # Find first non-divider course to get display_year
            display_year = None
            for course in courses_by_grade[grade_key]:
                if not course.get("is_divider", False):
                    display_year = course.get("display_year", "")
                    break

            # If all courses are transfers (only dividers), calculate year
            if not display_year:
                grade_num = int(grade_key)
                year_offset = 12 - grade_num
                end_year = grad_year - year_offset
                start_year = end_year - 1
                display_year = f"{start_year} - {end_year}"

            grade_metadata[grade_key] = {
                "display_year": display_year,
                "grade_level": f"{grade_key}th Grade",
                "weighted_gpa": year_gpas.get(grade_key, 0.0),
                "unweighted_gpa": year_gpas.get(f"{grade_key}_uw", 0.0),
            }
            logger.info(f"  Grade {grade_key} display_year: {display_year}")
        elif int(grade_key) == current_grade:
            # Create metadata for current grade even if no completed courses
            # This ensures "In Progress" header displays correctly
            grade_num = int(grade_key)
            year_offset = 12 - grade_num
            end_year = grad_year - year_offset
            start_year = end_year - 1
            display_year = f"{start_year} - {end_year}"

            grade_metadata[grade_key] = {
                "display_year": display_year,
                "grade_level": f"{grade_key}th Grade",
                "weighted_gpa": 0.0,
                "unweighted_gpa": 0.0,
            }
            logger.info(
                f"  Grade {grade_key} display_year (current, no completed): {display_year}"
            )

    # === SCHOOL INFORMATION ===
    assets_dir = project_root / "assets"

    def split_address_lines(address: Optional[str]) -> tuple[str, str]:
        """Split a comma-delimited address into two display lines."""
        import math

        # Handle NaN, None, empty, or non-string values
        if address is None or (isinstance(address, float) and math.isnan(address)):
            return "", ""
        if not isinstance(address, str) or not address.strip():
            return "", ""

        normalized = address.replace("\n", ", ")
        parts = [part.strip() for part in normalized.split(",") if part.strip()]

        if len(parts) >= 3:
            second_part = parts[1].lower()
            apt_indicators = ("#", "apt", "unit", "suite", "ste", "apartment")
            matches_indicator = any(
                second_part.startswith(indicator) for indicator in apt_indicators
            )
            if matches_indicator:
                line1 = f"{parts[0]} {parts[1]}".strip()
                line2 = ", ".join(parts[2:])
            else:
                line1 = parts[0]
                line2 = ", ".join(parts[1:])
        elif len(parts) == 2:
            line1, line2 = parts
        else:
            tokens = address.split()
            midpoint = max(1, len(tokens) // 2)
            line1 = " ".join(tokens[:midpoint]).strip()
            line2 = " ".join(tokens[midpoint:]).strip()

        return line1, line2

    school_info = {
        "school_name": "Keswick Christian School",
        "school_address": "10101 54th Avenue North, St Petersburg, FL 33708",
        "school_phone": "(727) 393-9100",
        "school_website": "www.keswickchristian.org",
        "registrar_name": "Mark J Trotter",
        "school_logo_path": str(assets_dir / "logos" / "text logo kcs.png"),
        "watermark_path": str(assets_dir / "watermarks" / "watermark.jpg"),
    }

    (
        school_address_line1,
        school_address_line2,
    ) = split_address_lines(school_info["school_address"])

    (
        student_address_line1,
        student_address_line2,
    ) = split_address_lines(student_record.get("Home address"))

    # Remove "United States" from student address
    if student_address_line2:
        student_address_line2 = student_address_line2.replace(
            ", United States", ""
        ).replace(" United States", "")

    # === CALCULATE DIPLOMA DESIGNATION (PROJECTED) ===
    diploma_designation = calculate_diploma_designation(
        courses_by_grade, current_grade, grad_year
    )

    # === CALCULATE PRINCIPAL'S LIST ===
    # Add Principal's List awards to awards_by_year
    principals_list_by_year = calculate_principals_list(
        courses_by_grade, grade_metadata, gpa_calculator
    )
    for year, semesters in principals_list_by_year.items():
        if year not in awards_by_year:
            awards_by_year[year] = []

        # Consolidate semesters into a single award
        if len(semesters) > 0:
            semester_str = ", ".join([f"S{s}" for s in semesters])
            principals_award = AwardResult(
                award_name="Principal's List",
                award_type="academic",
                year_earned=year,
                semester=semester_str,  # "S1" or "S1, S2"
                details=None,
            )
            # Add to beginning of list (academic awards first)
            awards_by_year[year].insert(0, principals_award)

    # === FORMAT CLASS RANK FOR DISPLAY ===
    class_rank_display = None
    if class_rank:
        class_rank_display = {
            "rank": class_rank.rank,
            "total": class_rank.total_students,
            "decile": class_rank.decile,
            "rank_display": f"{class_rank.rank} of {class_rank.total_students}",
            "percentile_display": f"{class_rank.percentile:.1f}%",
        }

    # === ENCODE WATERMARK IMAGE TO BASE64 WITH GOLD COLOR ===
    watermark_base64 = ""
    watermark_path = Path(school_info["watermark_path"])
    if watermark_path.exists():
        try:
            from PIL import Image
            import io

            # Open and process the image
            with Image.open(watermark_path) as img:
                # Convert to RGBA if not already
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                # Split into RGBA channels
                r, g, b, a = img.split()

                # Create gold-tinted version
                # Gold color: #D4AF37 (RGB: 212, 175, 55)
                # Only colorize dark pixels, keep light/white pixels as-is
                pixels_r = r.load()
                pixels_g = g.load()
                pixels_b = b.load()
                pixels_a = a.load()
                width, height = img.size

                # Create new RGBA image for gold tinting
                gold_img = Image.new("RGBA", (width, height))
                gold_pixels = gold_img.load()

                if pixels_r and pixels_g and pixels_b and pixels_a and gold_pixels:
                    for y in range(height):
                        for x in range(width):
                            # Get original RGB values
                            orig_r = pixels_r[x, y]
                            orig_g = pixels_g[x, y]
                            orig_b = pixels_b[x, y]
                            orig_a = pixels_a[x, y]

                            # Calculate luminance (perceived brightness)
                            luminance = 0.299 * orig_r + 0.587 * orig_g + 0.114 * orig_b

                            # If pixel is bright (white/light), keep it white
                            # If pixel is dark, convert to gold
                            if luminance > 200:  # Threshold for "white" pixels
                                # Keep as white/original color
                                gold_pixels[x, y] = (orig_r, orig_g, orig_b, orig_a)
                            else:
                                # Dark pixel - convert to gold based on darkness
                                intensity = luminance / 255.0
                                gold_r = int(212 * intensity)
                                gold_g = int(175 * intensity)
                                gold_b = int(55 * intensity)
                                gold_pixels[x, y] = (gold_r, gold_g, gold_b, orig_a)

                    # Save to bytes
                    buffer = io.BytesIO()
                    gold_img.save(buffer, format="PNG")
                    watermark_base64 = base64.b64encode(buffer.getvalue()).decode(
                        "utf-8"
                    )

        except Exception as e:
            logger.warning(f"Could not process watermark image: {e}")

    # === ENCODE ACCREDITATION LOGOS TO BASE64 ===
    acsi_logo_base64 = ""
    cognia_logo_base64 = ""
    ap_gold_logo_base64 = ""

    logos_dir = project_root / "assets" / "logos"

    try:
        from PIL import Image
        import io

        # Encode ACSI logo
        acsi_path = logos_dir / "ACSI.jpg"
        if acsi_path.exists():
            with Image.open(acsi_path) as img:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG")
                acsi_logo_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # Encode Cognia logo
        cognia_path = logos_dir / "COGNIA.png"
        if cognia_path.exists():
            with Image.open(cognia_path) as img:
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                cognia_logo_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # Encode AP Platinum Honor Roll logo (upgraded from Gold)
        # Try PNG first, then fall back to webp
        ap_logo_path = logos_dir / "AP Platinum Honor Roll.png"
        if not ap_logo_path.exists():
            ap_logo_path = logos_dir / "AP Gold Honor Roll.webp"
        
        if ap_logo_path.exists():
            with Image.open(ap_logo_path) as img:
                # Convert to PNG for better compatibility
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                ap_gold_logo_base64 = base64.b64encode(buffer.getvalue()).decode(
                    "utf-8"
                )

    except Exception as e:
        logger.warning(f"Could not encode accreditation logos: {e}")

    # Encode signature images
    principal_signature_base64 = ""
    guidance_signature_base64 = ""

    try:
        signatures_dir = project_root / "assets" / "signature"

        # Encode Principal signature
        principal_sig_path = signatures_dir / "Lee Mortimer--Principal.png"
        if principal_sig_path.exists():
            with Image.open(principal_sig_path) as img:
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                principal_signature_base64 = base64.b64encode(buffer.getvalue()).decode(
                    "utf-8"
                )

        # Encode Guidance Director signature
        guidance_sig_path = signatures_dir / "Mark J Trotter--Guidance Director.png"
        if guidance_sig_path.exists():
            with Image.open(guidance_sig_path) as img:
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                guidance_signature_base64 = base64.b64encode(buffer.getvalue()).decode(
                    "utf-8"
                )

    except Exception as e:
        logger.warning(f"Could not encode signature images: {e}")

    # === CALCULATE PAGE-SPECIFIC ADAPTIVE SPACING ===
    # Page 1 (grades 9-10): No footer, more space available
    # Page 2 (grades 11-12): Has footer, less space, needs more compression

    # DEBUG: Log what grades are actually present
    logger.info(
        f"  Available grades in courses_by_grade: {list(courses_by_grade.keys())}"
    )

    # Count courses AND awards/distinctions per page (both take vertical space)
    page1_courses = 0  # Grades 9-10
    page2_courses = 0  # Grades 11-12
    page1_distinctions = 0
    page2_distinctions = 0

    for grade_key in ["9", "10"]:
        if grade_key in courses_by_grade:
            course_count = sum(
                1 for c in courses_by_grade[grade_key] if not c.get("is_divider", False)
            )
            logger.info(f"  Grade {grade_key}: {course_count} courses (Page 1)")
            page1_courses += course_count

        # Count awards/distinctions for this grade
        grade_year = grade_metadata.get(grade_key, {}).get("display_year", "")
        if grade_year and awards_by_year.get(grade_year):
            page1_distinctions += len(awards_by_year[grade_year])

    for grade_key in ["11", "12"]:
        if grade_key in courses_by_grade:
            course_count = sum(
                1 for c in courses_by_grade[grade_key] if not c.get("is_divider", False)
            )
            logger.info(f"  Grade {grade_key}: {course_count} courses (Page 2)")
            page2_courses += course_count

        # Count awards/distinctions for this grade
        grade_year = grade_metadata.get(grade_key, {}).get("display_year", "")
        if grade_year and awards_by_year.get(grade_year):
            page2_distinctions += len(awards_by_year[grade_year])

    # Count transfer dividers (each takes ~2.5 course rows of vertical space)
    page1_transfer_dividers = 0
    page2_transfer_dividers = 0

    if transfer_by_year_school:
        for grade_key in ["9", "10"]:
            if grade_key in transfer_by_year_school:
                # Count unique schools in this grade (each gets a divider)
                page1_transfer_dividers += len(transfer_by_year_school[grade_key])

        for grade_key in ["11", "12"]:
            if grade_key in transfer_by_year_school:
                # Count unique schools in this grade (each gets a divider)
                page2_transfer_dividers += len(transfer_by_year_school[grade_key])

    # Calculate "effective" course count (courses + distinctions/3 + dividers*2.5)
    # Each transfer divider adds ~2.5 course rows of height (bold text, borders, padding)
    # Also add Middle School credits which appear on Page 1 (1 row each)
    ms_credits_count = len(middle_school_credits)
    
    # Check for single page layout (footer on Page 1)
    is_single_page = (page2_courses == 0)

    # Count awards/distinctions for spacing (ALL awards appear on Page 1/Sidebar)
    # The template iterates ALL awards_by_year, so we must count them all.
    total_distinctions = sum(len(awards) for awards in awards_by_year.values())
    
    # We attribute all distinctions to Page 1 for spacing calculation if single page, 
    # or split them if multipage (but usually they are in sidebar).
    # Simplification: Add total_distinctions to page1_effective.
    
    page1_effective = (
        page1_courses + 
        ms_credits_count + 
        (total_distinctions / 3.0) + 
        (page1_transfer_dividers * 2.5)
    )
    # Page 2 effective doesn't need distinctions if they are in sidebar? 
    # In minimalist, distinctions are at bottom of grades.
    # If multipage, they are on Page 2?
    # Logic in template: {% if not single_page_layout %}... awards on Page 2 ... {% endif %}
    # If single page, awards on Page 1.
    
    # So:
    if is_single_page:
        # All distinctions on Page 1
        page1_effective = (
            page1_courses + 
            ms_credits_count + 
            (total_distinctions / 3.0) + 
            (page1_transfer_dividers * 2.5)
        )
        page2_effective = 0
    else:
        # Distinctions on Page 2
        page1_effective = (
            page1_courses + 
            ms_credits_count + 
            (page1_transfer_dividers * 2.5)
        )
        page2_effective = (
            page2_courses + (total_distinctions / 3.0) + (page2_transfer_dividers * 2.5)
        )

    # SMART OVERFLOW CHECK:
    # If single page but content is too heavy (> 10.5 effective), force Multi-Page.
    # This moves footer and distinctions to Page 2, freeing up Page 1.
    if is_single_page and page1_effective > 10.5:
        logger.info(f"  ⚠️  Content too heavy for single page ({page1_effective:.1f} > 10.5). Forcing Multi-Page.")
        is_single_page = False
        
        # Recalculate assuming Multi-Page (Distinctions move to Page 2)
        page1_effective = (
            page1_courses + 
            ms_credits_count + 
            (page1_transfer_dividers * 2.5)
        )
        page2_effective = (
            page2_courses + (total_distinctions / 3.0) + (page2_transfer_dividers * 2.5)
        )

    # Determine spacing tier for each page
    
    if is_single_page:
        # Page 1 has footer - use stricter thresholds (same as Page 2)
        # John Snyder (Grade 9) overflowing with 8.3-10.0 effective. 
        # So comfortable must be very low.
        if page1_effective <= 6:
            page1_tier = "comfortable"
        elif page1_effective <= 9:
            page1_tier = "moderate"
        else:
            page1_tier = "ultra-compact"
    else:
        # Page 1 has NO footer - use generous thresholds
        if page1_effective <= 22:
            page1_tier = "comfortable"
        elif page1_effective <= 26:
            page1_tier = "moderate"
        else:
            page1_tier = "ultra-compact"

    # Page 2 thresholds (tighter - has footer, less space)
    if page2_effective <= 18:
        page2_tier = "comfortable"
    elif page2_effective <= 22:
        page2_tier = "moderate"
    else:
        page2_tier = "ultra-compact"

    # Use the more compressed tier overall to ensure both pages fit
    tier_priority = {"comfortable": 0, "moderate": 1, "ultra-compact": 2}
    spacing_tier = max([page1_tier, page2_tier], key=lambda t: tier_priority[t])

    logger.info(
        f"  Page 1 (9-10): {page1_courses} courses + {page1_distinctions} "
        f"distinctions + {page1_transfer_dividers} transfer dividers = "
        f"{page1_effective:.1f} effective -> {page1_tier}"
    )
    logger.info(
        f"  Page 2 (11-12): {page2_courses} courses + {page2_distinctions} "
        f"distinctions + {page2_transfer_dividers} transfer dividers = "
        f"{page2_effective:.1f} effective -> {page2_tier}"
    )
    logger.info(f"  Final spacing tier: {spacing_tier}")

    # Calculate total for backward compatibility
    total_courses = page1_courses + page2_courses

    # Determine if single page layout (use the logic determined above)
    single_page_layout = is_single_page
    
    template_data = {
        "student": student_record,
        "gpa": gpa,
        "class_rank": class_rank_display,
        "diploma_designation": diploma_designation,
        "courses_by_grade": courses_by_grade,
        "grade_metadata": grade_metadata,
        "year_gpas": year_gpas,
        "middle_school_credits": middle_school_credits,
        "awards": awards,
        "awards_by_year": awards_by_year,
        "major_recognitions": major_recognitions,
        "test_scores": test_scores,
        "ap_scores": ap_scores,
        "ap_college_credits": ap_college_credits,
        "ap_awards": ap_awards,
        "sports_list": sports_list,
        "courses_in_progress": courses_in_progress,
        "current_grade": current_grade,
        "spacing_tier": spacing_tier,
        "single_page_layout": single_page_layout,
        "total_courses": total_courses,
        "transcript_type": "Official",
        "issue_date": datetime.now().strftime("%B %d, %Y"),
        "verification_code": f"KCS-{student_id}-{datetime.now().strftime('%Y%m%d')}",
        "watermark_base64": watermark_base64,
        "acsi_logo_base64": acsi_logo_base64,
        "cognia_logo_base64": cognia_logo_base64,
        "ap_gold_logo_base64": ap_gold_logo_base64,
        "principal_signature_base64": principal_signature_base64,
        "guidance_signature_base64": guidance_signature_base64,
        **school_info,
        "school_address_line1": school_address_line1,
        "school_address_line2": school_address_line2,
        "student_home_address_line1": student_address_line1,
        "student_home_address_line2": student_address_line2,
    }

    # Add layout metrics for auditing
    template_data["layout_metrics"] = {
        "page1_effective": round(page1_effective, 2),
        "page2_effective": round(page2_effective, 2),
        "spacing_tier": spacing_tier,
        "is_single_page": single_page_layout,
    }

    return template_data
