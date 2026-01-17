#!/usr/bin/env python3
"""
BATCH TRANSCRIPT GENERATOR
Generates all transcripts organized by grade level with comprehensive error checking.

Output structure:
~/Desktop/Transcripts/2025-2026/
├── Grade 9/
├── Grade 10/
├── Grade 11/
└── Grade 12/

Naming: FirstName LastName GradYear.pdf
"""

import sys
from pathlib import Path
import shutil
from tqdm import tqdm
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import traceback

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from transcript_generator import TranscriptGenerator
from gpa_calculator import GPACalculator
from class_rank_calculator import ClassRankCalculator
from data_models import CourseWeight


@dataclass
class GenerationResult:
    student_id: int
    student_name: str
    grade_level: int
    success: bool
    pdf_path: Optional[str]
    error: Optional[str]


def setup_output_folders(base_path: Path) -> Dict[int, Path]:
    """Create output folder structure and return grade-level paths."""
    folders = {}
    
    for grade in [9, 10, 11, 12]:
        grade_folder = base_path / f"Grade {grade}"
        grade_folder.mkdir(parents=True, exist_ok=True)
        folders[grade] = grade_folder
    
    return folders


def run_pre_generation_checks(data_processor) -> Tuple[int, int, List[str]]:
    """Run screening checks and return (errors, warnings, critical_issues)."""
    from screen_transcripts import run_screening
    
    issues = run_screening(data_processor)
    
    errors = [i for i in issues if i.severity == "ERROR"]
    warnings = [i for i in issues if i.severity == "WARNING"]
    
    critical = [f"[{i.student_id}] {i.student_name}: {i.details}" for i in errors]
    
    return len(errors), len(warnings), critical


def generate_all_transcripts(
    generator: TranscriptGenerator,
    output_folders: Dict[int, Path],
    progress: bool = True
) -> List[GenerationResult]:
    """Generate transcripts for all students, organized by grade level."""
    import gc
    import logging
    
    # Reduce logging verbosity during batch
    logging.getLogger('weasyprint').setLevel(logging.ERROR)
    logging.getLogger('transcript_generator').setLevel(logging.WARNING)
    logging.getLogger('transcript_generator_minimalist').setLevel(logging.WARNING)
    logging.getLogger('decile_rank_calculator').setLevel(logging.WARNING)
    
    results = []
    students = generator.data_processor.student_details
    
    # Filter to only full-time students (those with GPA calculations)
    student_ids_with_gpa = set(generator.data_processor.gpa_results.keys())
    
    students_to_process = students[
        students["User ID"].isin(student_ids_with_gpa)
    ]
    
    print(f"\n📊 Processing {len(students_to_process)} full-time students")
    print(f"   (Skipping {len(students) - len(students_to_process)} part-time students)")
    
    iterator = tqdm(students_to_process.iterrows(), total=len(students_to_process), 
                   desc="Generating", unit="transcript") if progress else students_to_process.iterrows()
    
    for idx, (_, student) in enumerate(iterator):
        user_id = int(student["User ID"])
        first_name = str(student["First name"]).strip()
        last_name = str(student["Last name"]).strip()
        grad_year = int(student["Graduation year"])
        
        # Calculate current grade level
        current_year = 2026  # School year ending
        grade_level = 12 - (grad_year - current_year)
        
        # Clamp to valid range
        if grade_level < 9:
            grade_level = 9
        elif grade_level > 12:
            grade_level = 12
        
        # Build output filename
        clean_first = first_name.replace('"', '').replace("'", "")
        clean_last = last_name.replace('"', '').replace("'", "")
        filename = f"{clean_first} {clean_last} {grad_year}.pdf"
        output_path = output_folders[grade_level] / filename
        
        try:
            # Generate transcript
            pdf_path = generator.generate_transcript(
                user_id,
                layout="minimalist",
                output_filename=str(output_path)
            )
            
            # Copy to correct folder if needed
            if Path(pdf_path) != output_path:
                shutil.copy2(pdf_path, output_path)
            
            results.append(GenerationResult(
                student_id=user_id,
                student_name=f"{first_name} {last_name}",
                grade_level=grade_level,
                success=True,
                pdf_path=str(output_path),
                error=None
            ))
            
        except Exception as e:
            results.append(GenerationResult(
                student_id=user_id,
                student_name=f"{first_name} {last_name}",
                grade_level=grade_level,
                success=False,
                pdf_path=None,
                error=str(e)
            ))
            if progress:
                tqdm.write(f"  ❌ Failed {user_id}: {str(e)[:50]}")
        
        # Force garbage collection every 5 transcripts to prevent memory buildup
        if (idx + 1) % 5 == 0:
            gc.collect()
    
    return results


def print_summary(results: List[GenerationResult], output_base: Path):
    """Print generation summary."""
    success = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    print("\n" + "="*70)
    print("BATCH GENERATION SUMMARY")
    print("="*70)
    
    print(f"\n✅ Successful: {len(success)}")
    print(f"❌ Failed: {len(failed)}")
    
    # By grade level
    print("\nBy Grade Level:")
    for grade in [9, 10, 11, 12]:
        grade_success = len([r for r in success if r.grade_level == grade])
        grade_failed = len([r for r in failed if r.grade_level == grade])
        print(f"  Grade {grade}: {grade_success} generated, {grade_failed} failed")
    
    if failed:
        print("\n❌ FAILED TRANSCRIPTS:")
        print("-"*50)
        for r in failed:
            print(f"  [{r.student_id}] {r.student_name}")
            print(f"      Error: {r.error[:80]}..." if len(r.error) > 80 else f"      Error: {r.error}")
    
    print(f"\n📁 Output: {output_base}")
    print("="*70)


def main():
    # Configuration
    OUTPUT_BASE = Path.home() / "Desktop" / "Transcripts" / "2025-2026"
    
    print("="*70)
    print("BATCH TRANSCRIPT GENERATOR")
    print("="*70)
    
    # Initialize generator
    print("\n📂 Initializing transcript generator...")
    generator = TranscriptGenerator()
    
    print("📊 Loading all data...")
    if not generator.data_processor.load_all_data():
        print("❌ Failed to load data!")
        return 1
    
    # Initialize GPA Calculator - using correct CourseWeight format
    course_weights = {}
    for _, row in generator.data_processor.gpa_weight_index.iterrows():
        cw = CourseWeight(
            course_id=int(row["courseID"]),
            course_code=str(row["course_code"]),
            course_title=str(row["course_title"]),
            core=(str(row["CORE"]).upper() == "YES"),
            weight=float(row["weight"]),
            credit=float(row["credit"])
        )
        course_weights[cw.course_code] = cw
    
    generator.gpa_calculator = GPACalculator(course_weights)
    
    # Initialize Class Rank Calculator
    generator.rank_calculator = ClassRankCalculator()
    
    # Populate Rankings with (user_id, weighted_gpa) tuples
    student_gpas = []
    for uid, gpa_res in generator.data_processor.gpa_results.items():
        student_gpas.append((uid, gpa_res.core_weighted_gpa))
    
    generator.rank_calculator.calculate_class_rankings(student_gpas)
    
    # Run pre-generation screening
    print("\n🔍 Running pre-generation quality checks...")
    errors, warnings, critical = run_pre_generation_checks(generator.data_processor)
    
    print(f"   Errors: {errors}, Warnings: {warnings}")
    
    if errors > 0:
        print("\n🚨 BLOCKING ERRORS FOUND:")
        for issue in critical:
            print(f"   {issue}")
        print("\n❌ Fix errors before proceeding!")
        return 1
    
    if warnings > 0:
        print(f"   ⚠️  {warnings} warnings (mostly part-time students - expected)")
    
    # Setup output folders
    print(f"\n📁 Creating output structure: {OUTPUT_BASE}")
    
    # Remove if exists for clean start
    if OUTPUT_BASE.exists():
        print("   Removing existing folder...")
        shutil.rmtree(OUTPUT_BASE)
    
    output_folders = setup_output_folders(OUTPUT_BASE)
    print("   ✅ Created Grade 9, 10, 11, 12 folders")
    
    # Generate all transcripts
    print("\n🚀 Starting batch generation...")
    results = generate_all_transcripts(generator, output_folders, progress=True)
    
    # Print summary
    print_summary(results, OUTPUT_BASE)
    
    # Return success/failure
    failed_count = len([r for r in results if not r.success])
    if failed_count > 0:
        print(f"\n⚠️  {failed_count} transcripts failed - review errors above")
        return 1
    else:
        print("\n✅ All transcripts generated successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
