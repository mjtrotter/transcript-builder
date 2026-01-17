#!/usr/bin/env python3
"""
Decile-Based Class Rank Calculator
Ranks students by CORE Weighted GPA within their grade level
Excludes part-time students (< 5 courses)
Groups into deciles with smart rounding
"""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DecileRankResult:
    """Decile-based ranking result"""

    user_id: int
    rank: int
    total_students: int
    decile: str  # "1st Decile", "2nd Decile", etc.
    percentile: float
    core_weighted_gpa: float
    is_part_time: bool


def calculate_decile_ranks(
    student_gpas: List[
        Tuple[int, float, int]
    ],  # (user_id, core_weighted_gpa, course_count)
    graduation_year: int,
) -> Dict[int, DecileRankResult]:
    """
    Calculate decile-based class ranks

    Args:
        student_gpas: List of (user_id, core_weighted_gpa, course_count) tuples
        graduation_year: Graduation year for this cohort

    Returns:
        Dict mapping user_id to DecileRankResult
    """

    # Filter out part-time students (< 5 courses)
    full_time_students = [
        (uid, gpa, count) for uid, gpa, count in student_gpas if count >= 5
    ]
    part_time_students = [
        (uid, gpa, count) for uid, gpa, count in student_gpas if count < 5
    ]

    logger.info(
        f"Grad {graduation_year}: {len(full_time_students)} full-time, {len(part_time_students)} part-time"
    )

    # Sort by GPA descending (highest first)
    full_time_students.sort(key=lambda x: x[1], reverse=True)

    total_students = len(full_time_students)
    results = {}

    # Calculate decile sizes with smart distribution
    decile_sizes = calculate_decile_distribution(total_students)

    logger.info(f"Decile distribution for {total_students} students: {decile_sizes}")

    # Assign ranks and deciles
    current_rank = 1
    decile_index = 0
    students_in_current_decile = 0

    for uid, gpa, course_count in full_time_students:
        # Determine decile (1-10)
        if (
            students_in_current_decile >= decile_sizes[decile_index]
            and decile_index < 9
        ):
            decile_index += 1
            students_in_current_decile = 0

        decile_num = decile_index + 1
        decile_name = format_decile_name(decile_num)

        percentile = (current_rank / total_students) * 100

        results[uid] = DecileRankResult(
            user_id=uid,
            rank=current_rank,
            total_students=total_students,
            decile=decile_name,
            percentile=percentile,
            core_weighted_gpa=gpa,
            is_part_time=False,
        )

        current_rank += 1
        students_in_current_decile += 1

    # Handle part-time students separately
    for uid, gpa, course_count in part_time_students:
        results[uid] = DecileRankResult(
            user_id=uid,
            rank=0,
            total_students=total_students,
            decile="Part-Time",
            percentile=0,
            core_weighted_gpa=gpa,
            is_part_time=True,
        )

    return results


def calculate_decile_distribution(total_students: int) -> List[int]:
    """
    Calculate decile distribution with smart rounding

    For 43 students:
    - Base size: 4 per decile
    - Remainder: 3 students
    - Distribution: [5, 5, 5, 4, 4, 4, 4, 4, 4, 4] (top 3 deciles get +1)

    For 37 students:
    - Base size: 3 per decile
    - Remainder: 7 students
    - Distribution: [4, 4, 4, 4, 4, 4, 4, 3, 3, 3] (top 7 deciles get +1)
    """

    base_size = total_students // 10
    remainder = total_students % 10

    # Start with base size for all deciles
    decile_sizes = [base_size] * 10

    # Distribute remainder to top deciles
    for i in range(remainder):
        decile_sizes[i] += 1

    return decile_sizes


def format_decile_name(decile_num: int) -> str:
    """Format decile number with ordinal suffix"""
    ordinals = {
        1: "1st Decile",
        2: "2nd Decile",
        3: "3rd Decile",
        4: "4th Decile",
        5: "5th Decile",
        6: "6th Decile",
        7: "7th Decile",
        8: "8th Decile",
        9: "9th Decile",
        10: "10th Decile",
    }
    return ordinals.get(decile_num, f"{decile_num}th Decile")


def get_student_decile_rank(
    user_id: int, rankings: Dict[int, DecileRankResult]
) -> Optional[DecileRankResult]:
    """Get decile rank for specific student"""
    return rankings.get(user_id)


def get_top_students(
    rankings: Dict[int, DecileRankResult], n: int = 10
) -> List[DecileRankResult]:
    """Get top N students by rank"""
    ranked_students = sorted(rankings.values(), key=lambda x: x.rank)
    return [s for s in ranked_students if not s.is_part_time][:n]


def format_rank_display(rank_result: DecileRankResult) -> str:
    """Format rank for display"""
    if rank_result.is_part_time:
        return "Part-Time Student"
    return f"{rank_result.rank} of {rank_result.total_students}"
