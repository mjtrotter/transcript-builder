#!/usr/bin/env python3
"""
CLASS RANK CALCULATOR - Calculate student class rankings from GPA data
Determine class rank, percentile, and decile classifications

RANKING METHODOLOGY:
✅ Primary Sort: CORE Weighted GPA (descending)
✅ Tie Handling: Students with identical GPAs receive same rank
✅ Rank Gaps: After ties, next rank skips (e.g., two #1s, next is #3)
✅ Percentile: Rank position / Total students * 100
✅ Decile: Group into 10ths (Top 10%, Top 20%, etc.)

OUTPUT FORMATS:
- Numeric: "Rank 15 of 190"
- Percentile: "Top 8%"
- Decile: "1st Decile" or "Top 10%"
- Quartile: "Top Quartile"

Priority: HIGH - Essential for college admissions
Dependencies: pandas, data_processor, gpa_calculator
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ClassRankResult:
    """Class rank calculation result for a student"""
    user_id: int
    rank: int
    total_students: int
    percentile: float
    decile: str
    quartile: str
    quintile: str

    @property
    def rank_display(self) -> str:
        """Get formatted rank display"""
        return f"{self.rank} of {self.total_students}"

    @property
    def percentile_display(self) -> str:
        """Get formatted percentile display"""
        if self.percentile <= 1:
            return "Top 1%"
        elif self.percentile <= 5:
            return "Top 5%"
        elif self.percentile <= 10:
            return "Top 10%"
        elif self.percentile <= 25:
            return "Top 25%"
        elif self.percentile <= 50:
            return "Top Half"
        else:
            return f"Top {int(self.percentile)}%"


class ClassRankCalculator:
    """Calculate class rankings based on GPA data"""

    def __init__(self):
        self.rankings: Dict[int, ClassRankResult] = {}
        self.ranking_log: List[str] = []

    def calculate_class_rankings(
        self,
        student_gpas: List[Tuple[int, float]],
        graduation_year: Optional[int] = None
    ) -> Dict[int, ClassRankResult]:
        """
        Calculate class rankings for all students

        Args:
            student_gpas: List of (user_id, core_weighted_gpa) tuples
            graduation_year: Optional filter for specific graduating class

        Returns:
            Dictionary mapping user_id to ClassRankResult
        """
        self.ranking_log = []
        self.ranking_log.append(f"🏆 Calculating class rankings for {len(student_gpas)} students")

        if graduation_year:
            self.ranking_log.append(f"   Filtering for Class of {graduation_year}")

        # Sort by GPA descending (highest first)
        sorted_students = sorted(student_gpas, key=lambda x: x[1], reverse=True)

        # Calculate rankings with tie handling
        rankings = {}
        current_rank = 1
        previous_gpa = None
        students_at_current_rank = 0

        for i, (user_id, gpa) in enumerate(sorted_students):
            # Handle ties - same GPA gets same rank
            if previous_gpa is not None and abs(gpa - previous_gpa) < 0.001:  # Same GPA (within rounding)
                rank = current_rank
                students_at_current_rank += 1
            else:
                # New rank - skip positions for previous ties
                if students_at_current_rank > 1:
                    current_rank += students_at_current_rank
                    students_at_current_rank = 1
                else:
                    current_rank = i + 1
                    students_at_current_rank = 1
                rank = current_rank

            # Calculate percentile
            percentile = (rank / len(sorted_students)) * 100

            # Calculate decile
            decile = self._calculate_decile(percentile)

            # Calculate quartile
            quartile = self._calculate_quartile(percentile)

            # Calculate quintile
            quintile = self._calculate_quintile(percentile)

            # Create result
            result = ClassRankResult(
                user_id=user_id,
                rank=rank,
                total_students=len(sorted_students),
                percentile=percentile,
                decile=decile,
                quartile=quartile,
                quintile=quintile
            )

            rankings[user_id] = result
            previous_gpa = gpa

            # Log top 10
            if rank <= 10:
                self.ranking_log.append(
                    f"   #{rank}: Student {user_id} - GPA {gpa:.3f} - {result.percentile_display}"
                )

        self.rankings = rankings

        self.ranking_log.append(f"✅ Rankings calculated successfully")
        self.ranking_log.append(f"   Rank range: 1 to {len(sorted_students)}")
        self.ranking_log.append(f"   Top GPA: {sorted_students[0][1]:.3f}")
        self.ranking_log.append(f"   Median GPA: {sorted_students[len(sorted_students)//2][1]:.3f}")

        return rankings

    def _calculate_decile(self, percentile: float) -> str:
        """Calculate decile classification"""
        if percentile <= 10:
            return "1st Decile (Top 10%)"
        elif percentile <= 20:
            return "2nd Decile (Top 20%)"
        elif percentile <= 30:
            return "3rd Decile (Top 30%)"
        elif percentile <= 40:
            return "4th Decile (Top 40%)"
        elif percentile <= 50:
            return "5th Decile (Top 50%)"
        elif percentile <= 60:
            return "6th Decile"
        elif percentile <= 70:
            return "7th Decile"
        elif percentile <= 80:
            return "8th Decile"
        elif percentile <= 90:
            return "9th Decile"
        else:
            return "10th Decile"

    def _calculate_quartile(self, percentile: float) -> str:
        """Calculate quartile classification"""
        if percentile <= 25:
            return "1st Quartile (Top 25%)"
        elif percentile <= 50:
            return "2nd Quartile (Top 50%)"
        elif percentile <= 75:
            return "3rd Quartile"
        else:
            return "4th Quartile"

    def _calculate_quintile(self, percentile: float) -> str:
        """Calculate quintile classification"""
        if percentile <= 20:
            return "1st Quintile (Top 20%)"
        elif percentile <= 40:
            return "2nd Quintile (Top 40%)"
        elif percentile <= 60:
            return "3rd Quintile"
        elif percentile <= 80:
            return "4th Quintile"
        else:
            return "5th Quintile"

    def get_student_rank(self, user_id: int) -> Optional[ClassRankResult]:
        """Get rank for specific student"""
        return self.rankings.get(user_id)

    def get_top_students(self, n: int = 10) -> List[Tuple[int, ClassRankResult]]:
        """Get top N students by rank"""
        sorted_rankings = sorted(
            self.rankings.items(),
            key=lambda x: x[1].rank
        )
        return sorted_rankings[:n]

    def get_students_by_decile(self, decile: int) -> List[int]:
        """Get all student IDs in a specific decile (1-10)"""
        students = []
        for user_id, result in self.rankings.items():
            if f"{decile}" in result.decile or (decile == 1 and "Top 10%" in result.decile):
                students.append(user_id)
        return students

    def generate_ranking_report(self, output_path: Optional[Path] = None) -> pd.DataFrame:
        """
        Generate comprehensive ranking report

        Args:
            output_path: Optional path to save CSV report

        Returns:
            DataFrame with all ranking information
        """
        if not self.rankings:
            logger.warning("No rankings calculated yet")
            return pd.DataFrame()

        # Convert to DataFrame
        records = []
        for user_id, result in self.rankings.items():
            records.append({
                'User ID': user_id,
                'Rank': result.rank,
                'Total Students': result.total_students,
                'Percentile': f"{result.percentile:.1f}%",
                'Decile': result.decile,
                'Quartile': result.quartile,
                'Quintile': result.quintile,
                'Rank Display': result.rank_display,
                'Percentile Display': result.percentile_display
            })

        df = pd.DataFrame(records)
        df = df.sort_values('Rank')

        if output_path:
            df.to_csv(output_path, index=False)
            logger.info(f"Ranking report saved to: {output_path}")

        return df

    def get_ranking_log(self) -> List[str]:
        """Get detailed ranking calculation log"""
        return self.ranking_log


def main():
    """Test class rank calculator"""

    print("🏆 CLASS RANK CALCULATOR TEST")
    print("=" * 60)

    # Load actual student GPA data from validation results
    try:
        validation_file = Path(__file__).parent.parent / "GPA_VALIDATION_RESULTS.csv"

        if validation_file.exists():
            print(f"📊 Loading GPA data from: {validation_file.name}")
            df = pd.read_csv(validation_file)

            # Extract user_id and CORE weighted GPA
            student_gpas = [
                (row['student_id'], row['calculated_core_weighted'])
                for _, row in df.iterrows()
                if pd.notna(row['calculated_core_weighted'])
            ]

            print(f"✅ Loaded {len(student_gpas)} students with GPAs")

        else:
            print("⚠️ Validation file not found, using sample data")
            # Sample data for testing
            student_gpas = [
                (1001, 4.65),
                (1002, 4.61),
                (1003, 4.60),
                (1004, 4.55),
                (1005, 4.50),
                (1006, 4.50),  # Tie
                (1007, 4.45),
                (1008, 4.40),
                (1009, 4.35),
                (1010, 4.30),
                (1011, 3.80),
                (1012, 3.50),
                (1013, 3.20),
                (1014, 2.90),
                (1015, 2.50),
            ]

    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return

    # Initialize calculator
    calculator = ClassRankCalculator()

    # Calculate rankings
    rankings = calculator.calculate_class_rankings(student_gpas)

    # Display calculation log
    print(f"\n📝 Calculation Log:")
    for log_entry in calculator.get_ranking_log():
        print(f"  {log_entry}")

    # Display top 10
    print(f"\n🏆 TOP 10 STUDENTS:")
    print("-" * 80)
    top_students = calculator.get_top_students(10)

    for user_id, result in top_students:
        print(f"  #{result.rank:3d} | Student {user_id:6d} | {result.percentile_display:15s} | {result.decile}")

    # Display specific student lookup
    if top_students:
        test_student_id = top_students[0][0]
        result = calculator.get_student_rank(test_student_id)
        print(f"\n🔍 Sample Student Lookup (ID: {test_student_id}):")
        print(f"  Rank: {result.rank_display}")
        print(f"  Percentile: {result.percentile_display}")
        print(f"  Decile: {result.decile}")
        print(f"  Quartile: {result.quartile}")

    # Generate and save report
    output_path = Path(__file__).parent.parent / "CLASS_RANKINGS_REPORT.csv"
    df = calculator.generate_ranking_report(output_path)

    print(f"\n📊 Ranking Statistics:")
    print(f"  Total Students: {len(rankings)}")
    print(f"  Top Decile (Top 10%): {len(calculator.get_students_by_decile(1))} students")
    print(f"  Report saved to: {output_path.name}")

    print("\n✅ Class rank calculator test complete!")


if __name__ == "__main__":
    main()