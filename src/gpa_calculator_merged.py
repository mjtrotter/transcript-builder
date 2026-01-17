"""
GPA Calculator using Merged Grade Dataset
Simplified calculator that works with the clean Merged_Grades.csv dataset.

Rules:
- Only CORE classes count toward GPA
- Term GPAs filter by academic year
- Cumulative GPA is all years combined
- Credits attempted = credits earned (unless grade is F)
- Blank grades already excluded from merged dataset
"""

import pandas as pd
from typing import Dict, Tuple


class MergedGPACalculator:
    """Calculate GPAs from the merged grade dataset"""

    # Grade to points mapping
    GRADE_POINTS = {
        "A": 4.0,
        "A+": 4.0,
        "A-": 3.67,
        "B+": 3.33,
        "B": 3.0,
        "B-": 2.67,
        "C+": 2.33,
        "C": 2.0,
        "C-": 1.67,
        "D+": 1.33,
        "D": 1.0,
        "D-": 0.67,
        "F": 0.0,
        # Numeric grades (convert to 4.0 scale)
        "100": 4.0,
        "99": 4.0,
        "98": 4.0,
        "97": 4.0,
        "96": 4.0,
        "95": 4.0,
        "94": 4.0,
        "93": 4.0,
        "92": 4.0,
        "91": 4.0,
        "90": 4.0,
        "89": 3.67,
        "88": 3.67,
        "87": 3.67,
        "86": 3.33,
        "85": 3.33,
        "84": 3.33,
        "83": 3.0,
        "82": 3.0,
        "81": 3.0,
        "80": 3.0,
        "79": 2.67,
        "78": 2.67,
        "77": 2.67,
        "76": 2.33,
        "75": 2.33,
        "74": 2.33,
        "73": 2.0,
        "72": 2.0,
        "71": 2.0,
        "70": 2.0,
        "69": 1.67,
        "68": 1.67,
        "67": 1.67,
        "66": 1.33,
        "65": 1.33,
        "64": 1.33,
        "63": 1.0,
        "62": 1.0,
        "61": 1.0,
        "60": 1.0,
        "59": 0.0,
        "58": 0.0,
        "57": 0.0,
        "56": 0.0,
        "55": 0.0,
        "54": 0.0,
        "53": 0.0,
        "52": 0.0,
        "51": 0.0,
        "50": 0.0,
    }

    def __init__(self, merged_grades_path: str):
        """Initialize with path to Merged_Grades.csv"""
        self.df = pd.read_csv(merged_grades_path)
        print(f"📊 Loaded {len(self.df):,} grade records from merged dataset")
        print(f"   Students: {self.df['User ID'].nunique()}")
        print(f"   CORE courses: {len(self.df[self.df['CORE'] == 'Yes']):,}")

    def _grade_to_points(self, grade: str) -> float:
        """Convert letter or numeric grade to points"""
        grade = str(grade).strip().upper()
        return self.GRADE_POINTS.get(grade, 0.0)

    def _is_passing(self, grade: str) -> bool:
        """Check if grade is passing (not F)"""
        points = self._grade_to_points(grade)
        return points > 0.0

    def calculate_gpa(
        self, user_id: int, academic_year: str = None, weighted: bool = True
    ) -> Tuple[float, float, float]:
        """
        Calculate GPA for a student

        Args:
            user_id: Student ID
            academic_year: Specific year (e.g. "2024 - 2025") or None for cumulative
            weighted: True for weighted GPA, False for unweighted

        Returns:
            (gpa, credits_attempted, credits_earned)
        """
        # Get student's courses (include ALL for credit totals)
        # Filter is applied inside loop for GPA (CORE only)
        student_df = self.df[self.df["User ID"] == user_id].copy()

        # Filter by year if specified
        if academic_year:
            student_df = student_df[student_df["Academic Year"] == academic_year]

        if len(student_df) == 0:
            return 0.0, 0.0, 0.0

        # Calculate GPA (Core Only) and Credits (All)
        total_gpa_points = 0.0
        total_gpa_credits = 0.0
        
        total_credits_attempted = 0.0
        total_credits_earned = 0.0

        for _, course in student_df.iterrows():
            # Get credits for this course
            try:
                credits = float(course["Credit Earned"])
            except (ValueError, TypeError):
                credits = 0.0

            total_credits_attempted += credits

            # 1. GPA Calculation (CORE ONLY)
            if course["CORE"] == "Yes":
                # Get grade points
                base_points = self._grade_to_points(course["Grade Earned"])
                
                # Add weight
                if weighted:
                    try:
                        weight = float(course["Weight"]) if pd.notna(course["Weight"]) else 0.0
                    except (ValueError, TypeError):
                        weight = 0.0
                    points = base_points + weight
                else:
                    points = base_points
                
                total_gpa_points += points * credits
                total_gpa_credits += credits

            # 2. Credits Earned (ALL PASSING COURSES)
            if self._is_passing(course["Grade Earned"]):
                total_credits_earned += credits

        # Calculate GPA
        gpa = total_gpa_points / total_gpa_credits if total_gpa_credits > 0 else 0.0

        return round(gpa, 6), round(total_credits_attempted, 2), round(total_credits_earned, 2)

    def calculate_all_term_gpas(
        self, user_id: int, weighted: bool = True
    ) -> Dict[str, Tuple[float, float]]:
        """
        Calculate GPA for each academic year (term)

        Returns:
            dict mapping year -> (gpa, credits)
        """
        # Get unique academic years for this student
        student_df = self.df[
            (self.df["User ID"] == user_id) & (self.df["CORE"] == "Yes")
        ]

        years = sorted(student_df["Academic Year"].unique())

        term_gpas = {}
        for year in years:
            gpa, credits_attempted, credits_earned = self.calculate_gpa(
                user_id, academic_year=year, weighted=weighted
            )
            term_gpas[year] = (gpa, credits_attempted)

        return term_gpas

    def calculate_cumulative_gpa(
        self, user_id: int, weighted: bool = True
    ) -> Dict[str, float]:
        """
        Calculate cumulative GPA across all years

        Returns:
            dict with 'gpa', 'credits_attempted', 'credits_earned'
        """
        gpa, credits_attempted, credits_earned = self.calculate_gpa(
            user_id, academic_year=None, weighted=weighted
        )

        return {
            "gpa": gpa,
            "credits_attempted": credits_attempted,
            "credits_earned": credits_earned,
        }

    def calculate_all_students(self, weighted: bool = True) -> pd.DataFrame:
        """
        Calculate cumulative GPA for all students

        Returns:
            DataFrame with columns: User ID, First Name, Last Name, GPA, Credits Attempted, Credits Earned
        """
        results = []

        student_ids = self.df["User ID"].unique()
        for user_id in student_ids:
            # Get student info
            student_info = self.df[self.df["User ID"] == user_id].iloc[0]

            # Calculate cumulative GPA
            cum = self.calculate_cumulative_gpa(user_id, weighted=weighted)

            results.append(
                {
                    "User ID": user_id,
                    "First Name": student_info["First Name"],
                    "Last Name": student_info["Last Name"],
                    "Cumulative GPA": cum["gpa"],
                    "Credits Attempted": cum["credits_attempted"],
                    "Credits Earned": cum["credits_earned"],
                }
            )

        return pd.DataFrame(results).sort_values("Cumulative GPA", ascending=False)


if __name__ == "__main__":
    # Test with Jacob
    calc = MergedGPACalculator("data/Merged_Grades.csv")

    print("\n" + "=" * 80)
    print("JACOB MABREY (User ID 7048596) - GPA CALCULATION TEST")
    print("=" * 80)

    # Term GPAs
    print("\nTERM GPAs (Weighted):")
    term_gpas = calc.calculate_all_term_gpas(7048596, weighted=True)
    for year, (gpa, credits) in term_gpas.items():
        print(f"  {year}: GPA {gpa:.2f} ({credits} credits)")

    # Cumulative
    print("\nCUMULATIVE GPA (Weighted):")
    cum_weighted = calc.calculate_cumulative_gpa(7048596, weighted=True)
    print(f"  GPA: {cum_weighted['gpa']:.4f}")
    print(f"  Credits Attempted: {cum_weighted['credits_attempted']}")
    print(f"  Credits Earned: {cum_weighted['credits_earned']}")

    print("\nCUMULATIVE GPA (Unweighted):")
    cum_unweighted = calc.calculate_cumulative_gpa(7048596, weighted=False)
    print(f"  GPA: {cum_unweighted['gpa']:.4f}")
    print(f"  Credits Attempted: {cum_unweighted['credits_attempted']}")
    print(f"  Credits Earned: {cum_unweighted['credits_earned']}")

    # Manual verification
    print("\n" + "=" * 80)
    print("MANUAL VERIFICATION:")
    print("Expected weighted GPA: 3.107 (from your calculation)")
    print("Expected credits: 17.0")
    print(f"Actual weighted GPA: {cum_weighted['gpa']:.4f}")
    print(f"Actual credits: {cum_weighted['credits_attempted']}")

    diff = abs(cum_weighted["gpa"] - 3.107)
    if diff < 0.01:
        print("✅ GPA matches expected value!")
    else:
        print(f"⚠️ GPA difference: {diff:.4f}")

    if cum_weighted["credits_attempted"] == 17.0:
        print("✅ Credits match expected value!")
    else:
        print(f"⚠️ Credit difference: {cum_weighted['credits_attempted'] - 17.0}")
