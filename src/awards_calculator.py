#!/usr/bin/env python3
"""
Awards and Honors Calculator
Calculates Principal's List, AP Scholar awards, ACSI honors, and NMSQT recognition
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AwardResult:
    """Individual award result"""
    award_name: str
    award_type: str  # 'academic', 'ap', 'testing', 'acsi'
    year_earned: Optional[str] = None
    semester: Optional[str] = None
    details: Optional[str] = None


def calculate_principals_list(student_grades: List[Dict], gpa_results: Dict) -> List[AwardResult]:
    """
    Calculate Principal's List awards per semester
    Criteria: Unweighted 4.0 GPA in ALL courses OR 4.4+ CORE Weighted GPA
    """
    awards = []

    # Group by year and semester
    semester_data = {}
    for grade in student_grades:
        year = grade.get('school_year')
        semester = grade.get('semester', 1)
        key = f"{year}-S{semester}"

        if key not in semester_data:
            semester_data[key] = []
        semester_data[key].append(grade)

    # Check each semester
    for semester_key, grades in semester_data.items():
        # Calculate unweighted GPA for all courses
        total_unweighted = 0
        count = 0

        # Calculate CORE weighted GPA
        core_weighted_total = 0
        core_count = 0

        for grade in grades:
            # Convert letter grade to points
            grade_letter = grade.get('grade', '')
            points = letter_to_points(grade_letter)

            if points is not None:
                total_unweighted += points
                count += 1

                # If CORE course, calculate weighted
                if grade.get('is_core', False):
                    weight = grade.get('weight', 0.0)
                    core_weighted_total += (points + weight)
                    core_count += 1

        # Check Principal's List criteria
        unweighted_gpa = (total_unweighted / count) if count > 0 else 0
        core_weighted_gpa = (core_weighted_total / core_count) if core_count > 0 else 0

        year_part = semester_key.split('-S')[0]
        semester_num = semester_key.split('-S')[1]

        if unweighted_gpa >= 4.0:
            awards.append(AwardResult(
                award_name="Principal's List",
                award_type="academic",
                year_earned=year_part,
                semester=f"Semester {semester_num}",
                details="Unweighted 4.0 GPA"
            ))
        elif core_weighted_gpa >= 4.4:
            awards.append(AwardResult(
                award_name="Principal's List",
                award_type="academic",
                year_earned=year_part,
                semester=f"Semester {semester_num}",
                details=f"CORE Weighted {core_weighted_gpa:.2f}"
            ))

    return awards


def calculate_ap_scholar_awards(ap_courses: List[Dict]) -> List[AwardResult]:
    """
    Calculate AP Scholar awards based on AP exam performance
    - AP Scholar: 3+ on 3+ AP exams
    - AP Scholar with Honor: Average 3.25+ on all AP exams, 3+ on 4+ exams
    - AP Scholar with Distinction: Average 3.5+ on all AP exams, 3+ on 5+ exams
    - AP Capstone Scholar: 3+ on both AP Seminar and AP Research
    - AP Capstone Diploma: 3+ on AP Seminar, AP Research, and 4+ additional AP exams
    """
    awards = []

    # Count AP exam scores (would need actual exam data)
    # For now, infer from AP courses taken
    ap_count = len(ap_courses)

    if ap_count >= 3:
        # Placeholder - would need actual exam scores
        awards.append(AwardResult(
            award_name="AP Scholar Candidate",
            award_type="ap",
            details=f"{ap_count} AP courses completed"
        ))

    return awards


def detect_acsi_honors(class_rank: int, total_students: int, core_weighted_gpa: float) -> List[AwardResult]:
    """
    Detect ACSI (Association of Christian Schools International) honors
    - Valedictorian: Rank #1 with 4.0+ GPA
    - Salutatorian: Rank #2 with 4.0+ GPA
    - DCHSS (Distinguished Christian High School Student): Top 10% with 3.5+ GPA
    """
    awards = []

    percentile = (class_rank / total_students) * 100

    if class_rank == 1 and core_weighted_gpa >= 4.0:
        awards.append(AwardResult(
            award_name="ACSI Valedictorian",
            award_type="acsi",
            details="Rank #1"
        ))
    elif class_rank == 2 and core_weighted_gpa >= 4.0:
        awards.append(AwardResult(
            award_name="ACSI Salutatorian",
            award_type="acsi",
            details="Rank #2"
        ))

    if percentile <= 10 and core_weighted_gpa >= 3.5:
        awards.append(AwardResult(
            award_name="ACSI DCHSS",
            award_type="acsi",
            details="Distinguished Christian High School Student"
        ))

    return awards


def detect_nmsqt_recognition(psat_score: Optional[int]) -> List[AwardResult]:
    """
    Detect National Merit Scholarship Qualifying Test recognition
    - Commended Student: ~207-211 (varies by year)
    - Semifinalist: ~212-224 (varies by state)
    - Finalist: Advance from semifinalist
    """
    awards = []

    if psat_score and psat_score >= 1400:
        # Convert to Selection Index (approximate)
        selection_index = int((psat_score / 1520) * 228)

        if selection_index >= 212:
            awards.append(AwardResult(
                award_name="NMSQT Semifinalist Candidate",
                award_type="testing",
                details=f"PSAT {psat_score}"
            ))
        elif selection_index >= 207:
            awards.append(AwardResult(
                award_name="NMSQT Commended Student Candidate",
                award_type="testing",
                details=f"PSAT {psat_score}"
            ))

    return awards


def letter_to_points(letter: str) -> Optional[float]:
    """Convert letter grade to GPA points"""
    grade_map = {
        'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0, 'F': 0.0
    }
    return grade_map.get(letter.upper())


def calculate_all_awards(
    student_grades: List[Dict],
    gpa_results: Dict,
    class_rank: Optional[int],
    total_students: Optional[int],
    test_scores: Dict
) -> List[AwardResult]:
    """Calculate all awards for a student"""

    all_awards = []

    # Principal's List
    try:
        principals_list = calculate_principals_list(student_grades, gpa_results)
        all_awards.extend(principals_list)
    except Exception as e:
        logger.warning(f"Error calculating Principal's List: {e}")

    # AP Scholar
    try:
        ap_courses = [g for g in student_grades if g.get('is_ap', False)]
        ap_awards = calculate_ap_scholar_awards(ap_courses)
        all_awards.extend(ap_awards)
    except Exception as e:
        logger.warning(f"Error calculating AP Scholar: {e}")

    # ACSI Honors
    if class_rank and total_students:
        try:
            core_gpa = gpa_results.get('core_weighted_gpa', 0)
            acsi_awards = detect_acsi_honors(class_rank, total_students, core_gpa)
            all_awards.extend(acsi_awards)
        except Exception as e:
            logger.warning(f"Error detecting ACSI honors: {e}")

    # NMSQT
    if test_scores.get('PSAT'):
        try:
            nmsqt_awards = detect_nmsqt_recognition(test_scores['PSAT'])
            all_awards.extend(nmsqt_awards)
        except Exception as e:
            logger.warning(f"Error detecting NMSQT: {e}")

    return all_awards
