#!/usr/bin/env python3
"""
Audit Layout Safety Script
Checks all students against layout density thresholds to identify potential overlaps.
"""

import sys
import os
from pathlib import Path
import pandas as pd
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from transcript_generator import TranscriptGenerator
from gpa_calculator import GPACalculator
from data_models import CourseWeight

def main():
    print("🚀 Starting Layout Safety Audit...")
    
    # Initialize generator
    generator = TranscriptGenerator()
    print("📊 Loading all data...")
    generator.data_processor.load_all_data()
    
    # Initialize GPA calculator (needed for weights/core status)
    print("🧮 Initializing GPA calculator...")
    course_weights = {}
    for _, row in generator.data_processor.gpa_weight_index.iterrows():
        # Handle potential NaN course codes
        if pd.isna(row["course_code"]):
            continue
            
        course_weights[row["course_code"]] = CourseWeight(
            course_id=int(row["courseID"]),
            course_code=str(row["course_code"]),
            course_title=row["course_title"],
            core=row["CORE"] == "Yes",
            weight=float(row["weight"]),
            credit=float(row["credit"]),
        )
    generator.gpa_calculator = GPACalculator(course_weights)

    # Get all students
    students = generator.data_processor.student_details
    total_students = len(students)
    print(f"🔍 Analyzing {total_students} students for layout risks...")
    
    results = []
    
    for _, student in tqdm(students.iterrows(), total=total_students):
        user_id = student["User ID"]
        first_name = student.get("First name", student.get("First Name", "Unknown"))
        last_name = student.get("Last name", student.get("Last Name", "Unknown"))
        grade_level = student.get("Student Grade Level", 12)
        
        try:
            metrics = generator.audit_student_layout(user_id)
            if not metrics:
                continue
                
            page1_effective = metrics.get("page1_effective", 0)
            page2_effective = metrics.get("page2_effective", 0)
            is_single_page = metrics.get("is_single_page", False)
            spacing_tier = metrics.get("spacing_tier", "unknown")
            
            # Risk Assessment Logic
            risk_level = "Safe"
            risk_details = ""
            
            if is_single_page:
                # Single Page Audit
                # Comfortable <= 6, Moderate <= 9, Compact > 9
                if page1_effective > 10.5: 
                    # High risk of overflow even in Compact?
                    # John Snyder was 10.0 and fit comfortably in Compact.
                    # Assuming 12+ might be risky? Use 11 as warning.
                    risk_level = "High"
                    risk_details = f"SinglePage Score {page1_effective:.1f} > 10.5"
                elif page1_effective > 9:
                    risk_level = "Monitor" # Forced Compact
                    risk_details = f"SinglePage Compact ({page1_effective:.1f})"
            else:
                # Multi Page Audit
                if page1_effective > 26: 
                    risk_level = "High"
                    risk_details = f"Page1 Score {page1_effective:.1f} > 26"
                elif page1_effective > 22:
                    risk_level = "Monitor"
                    
                if page2_effective > 22: # Footer on Page 2
                    if page2_effective > 24: # Risk?
                         risk_level = "High"
                         risk_details += f" P2 Score {page2_effective:.1f} > 24"
            
            results.append({
                "User ID": user_id,
                "Name": f"{first_name} {last_name}",
                "Grade": grade_level,
                "Type": "Single" if is_single_page else "Multi",
                "Tier": spacing_tier,
                "Score P1": page1_effective,
                "Score P2": page2_effective,
                "Risk": risk_level,
                "Details": risk_details
            })
            
        except Exception as e:
            print(f"Error checking student {user_id}: {e}")
            
    # Save Results
    if not results:
        print("❌ No results gathered. Check logs for errors.")
        return

    df_results = pd.DataFrame(results)
    
    # Ensure columns exist (if first row was different?)
    if "Risk" not in df_results.columns:
        print(f"❌ Error: 'Risk' column missing. Columns: {df_results.columns.tolist()}")
        print(df_results.head())
        # Force create if missing? No, logic ensures it.
        # Check if list of dicts was consistent.
        output_path = generator.project_root / "output" / "layout_audit_results_error.csv"
        df_results.to_csv(output_path, index=False)
        return

    output_path = generator.project_root / "output" / "layout_audit_results.csv"
    df_results.to_csv(output_path, index=False)
    
    # Print Summary
    high_risk = df_results[df_results["Risk"] == "High"]
    monitor = df_results[df_results["Risk"] == "Monitor"]
    
    print("\n" + "="*50)
    print("AUDIT COMPLETE")
    print("="*50)
    print(f"Total Students: {len(df_results)}")
    print(f"Safe: {len(df_results) - len(high_risk) - len(monitor)}")
    print(f"Monitor: {len(monitor)} (Forced Compact/Dense)")
    print(f"HIGH RISK: {len(high_risk)}")
    print("="*50)
    
    if len(high_risk) > 0:
        print("\n⚠️  HIGH RISK STUDENTS (Potential Overlap):")
        print(high_risk[["User ID", "Name", "Score P1", "Details"]].to_string(index=False))
        
    print(f"\nDetailed report saved to: {output_path}")

if __name__ == "__main__":
    main()
