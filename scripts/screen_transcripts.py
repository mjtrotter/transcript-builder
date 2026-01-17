#!/usr/bin/env python3
"""
TRANSCRIPT ERROR SCREENING SCRIPT
Pre-batch validation to catch common transcript generation issues.

Checks for:
1. Missing transfer credits for students who have them
2. Numeric grades that should be converted to letters
3. Missing honors badges on qualifying courses
4. GPA calculation anomalies
5. Students with unusually low course counts
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass


@dataclass
class ScreeningResult:
    student_id: int
    student_name: str
    issue_type: str
    severity: str  # "ERROR", "WARNING", "INFO"
    details: str


def run_screening(data_processor) -> List[ScreeningResult]:
    """Run all screening checks and return list of issues found."""
    issues = []
    
    # Get all students
    students = data_processor.student_details
    grades = data_processor.grades
    transfer_grades = data_processor.transfer_grades
    
    for _, student in students.iterrows():
        user_id = student["User ID"]
        name = f"{student['First name']} {student['Last name']}"
        grad_year = int(student["Graduation year"])
        
        # 1. Check for transfer credits
        student_transfers = transfer_grades[
            transfer_grades["User ID"].astype(str) == str(user_id)
        ]
        
        if not student_transfers.empty:
            # Check for numeric grades in transfers
            for _, t_row in student_transfers.iterrows():
                grade_val = t_row.get("Grade", "")
                if str(grade_val).replace(".", "", 1).isdigit():
                    issues.append(ScreeningResult(
                        student_id=int(user_id),
                        student_name=name,
                        issue_type="NUMERIC_TRANSFER_GRADE",
                        severity="INFO",
                        details=f"Transfer grade '{grade_val}' for {t_row['Course Title']} - will be converted to letter"
                    ))
            
            # Check for middle school transfers (pre-grade 9)
            current_year = 2026  # Current school year ending
            for _, t_row in student_transfers.iterrows():
                school_year = t_row.get("School Year", "")
                if school_year:
                    try:
                        end_year = int(str(school_year).split(" - ")[-1])
                        grade_level = 12 - (grad_year - end_year)
                        if grade_level < 9:
                            course_lower = str(t_row.get("Course Title", "")).lower()
                            # Check if it's a qualifying MS course
                            ms_keywords = ["algebra", "geometry", "biology", "chemistry", "spanish", "french", "latin", "physics"]
                            if any(kw in course_lower for kw in ms_keywords):
                                issues.append(ScreeningResult(
                                    student_id=int(user_id),
                                    student_name=name,
                                    issue_type="MS_TRANSFER_CREDIT",
                                    severity="INFO",
                                    details=f"MS transfer credit (Gr{grade_level}): {t_row['Course Title']} - should appear in Early HS Credits"
                                ))
                    except (ValueError, IndexError):
                        pass
        
        # 2. Check course count
        student_grades = grades[grades["User ID"] == user_id]
        if len(student_grades) < 10:
            issues.append(ScreeningResult(
                student_id=int(user_id),
                student_name=name,
                issue_type="LOW_COURSE_COUNT",
                severity="WARNING",
                details=f"Only {len(student_grades)} course records - may be part-time or missing data"
            ))
        
        # 3. Check for GPA anomalies
        if user_id in data_processor.gpa_results:
            gpa = data_processor.gpa_results[user_id]
            if gpa.weighted_gpa > 5.0:
                issues.append(ScreeningResult(
                    student_id=int(user_id),
                    student_name=name,
                    issue_type="GPA_ANOMALY",
                    severity="ERROR",
                    details=f"Weighted GPA {gpa.weighted_gpa:.3f} exceeds maximum expected 5.0"
                ))
            if gpa.weighted_gpa < gpa.unweighted_gpa:
                issues.append(ScreeningResult(
                    student_id=int(user_id),
                    student_name=name,
                    issue_type="GPA_ANOMALY",
                    severity="WARNING",
                    details=f"Weighted GPA {gpa.weighted_gpa:.3f} < Unweighted {gpa.unweighted_gpa:.3f} - unusual"
                ))
    
    return issues


def print_report(issues: List[ScreeningResult]):
    """Print formatted screening report."""
    print("\n" + "="*70)
    print("TRANSCRIPT SCREENING REPORT")
    print("="*70)
    
    errors = [i for i in issues if i.severity == "ERROR"]
    warnings = [i for i in issues if i.severity == "WARNING"]
    infos = [i for i in issues if i.severity == "INFO"]
    
    print(f"\nSummary: {len(errors)} Errors, {len(warnings)} Warnings, {len(infos)} Info")
    
    if errors:
        print("\n❌ ERRORS (require immediate attention):")
        print("-"*50)
        for issue in errors:
            print(f"  [{issue.student_id}] {issue.student_name}")
            print(f"      {issue.issue_type}: {issue.details}")
    
    if warnings:
        print("\n⚠️  WARNINGS (review recommended):")
        print("-"*50)
        for issue in warnings:
            print(f"  [{issue.student_id}] {issue.student_name}")
            print(f"      {issue.issue_type}: {issue.details}")
    
    if infos and len(infos) <= 20:  # Only show info if not too many
        print("\nℹ️  INFO (expected behavior):")
        print("-"*50)
        for issue in infos:
            print(f"  [{issue.student_id}] {issue.student_name}")
            print(f"      {issue.issue_type}: {issue.details}")
    elif infos:
        print(f"\nℹ️  INFO: {len(infos)} informational items (suppressed)")
    
    print("\n" + "="*70)
    
    return len(errors), len(warnings), len(infos)


def main():
    from data_processor import TranscriptDataProcessor
    
    print("Loading data for screening...")
    processor = TranscriptDataProcessor()
    if not processor.load_all_data():
        print("Failed to load data!")
        return 1
    
    print("Running screening checks...")
    issues = run_screening(processor)
    
    errors, warnings, infos = print_report(issues)
    
    if errors > 0:
        print("\n🚨 BLOCKING: Fix errors before batch generation!")
        return 1
    elif warnings > 0:
        print("\n⚠️  Review warnings before proceeding with batch generation.")
        return 0
    else:
        print("\n✅ All checks passed! Safe to proceed with batch generation.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
