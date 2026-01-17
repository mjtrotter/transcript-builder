#!/usr/bin/env python3
"""
Create Merged_Grades.csv from Grades.csv, Transfer Grades.csv, and GPA weight index.

This script combines:
1. Regular grades (from Grades.csv)
2. Transfer grades (from Transfer Grades.csv)
3. Course weight info (from GPA weight & credit index.csv)

Into a single merged file with columns:
- User ID, First Name, Last Name, Academic Year, Semester, Course Code, Course Title,
  Grade Earned, Credit Earned, CORE, Weight, School, Source
"""

import pandas as pd
from pathlib import Path
import sys


def create_merged_grades(data_dir: Path = None):
    """Create Merged_Grades.csv from component files."""
    
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / "data"
    else:
        data_dir = Path(data_dir)
    
    print("📊 Creating Merged Grades Dataset")
    print("=" * 60)
    
    # Load GPA weight index
    weight_path = data_dir / "GPA weight & credit index.csv"
    if not weight_path.exists():
        print(f"❌ Missing required file: {weight_path}")
        return False
    
    weights_df = pd.read_csv(weight_path, encoding="utf-8-sig")
    weight_lookup = {}
    for _, row in weights_df.iterrows():
        code = str(row["course_code"]).strip()
        weight_lookup[code] = {
            "CORE": row["CORE"],
            "Weight": row["weight"],
            "Credit": row["credit"]
        }
    print(f"  ✅ Loaded {len(weight_lookup)} course weight mappings")
    
    # Load regular grades
    grades_path = data_dir / "Grades.csv"
    if not grades_path.exists():
        print(f"❌ Missing required file: {grades_path}")
        return False
    
    grades_df = pd.read_csv(grades_path, encoding="utf-8-sig")
    print(f"  ✅ Loaded {len(grades_df)} regular grade records")
    
    # Load transfer grades
    transfer_path = data_dir / "Transfer Grades.csv"
    transfer_df = pd.DataFrame()
    if transfer_path.exists():
        transfer_df = pd.read_csv(transfer_path, encoding="utf-8-sig")
        print(f"  ✅ Loaded {len(transfer_df)} transfer grade records")
    else:
        print(f"  ⚠️ No transfer grades file found")
    
    # Process regular grades
    merged_records = []
    
    for _, row in grades_df.iterrows():
        course_code = str(row.get("Course Code", "")).strip()
        weight_info = weight_lookup.get(course_code, {"CORE": "No", "Weight": 0.0, "Credit": 1.0})
        
        # Skip blank grades
        grade = str(row.get("Grade", "")).strip()
        if not grade or grade.lower() in ["nan", ""]:
            continue
        
        # Determine semester
        semester = int(row.get("Course part number", 1))
        
        record = {
            "User ID": row.get("User ID"),
            "First Name": row.get("First Name"),
            "Last Name": row.get("Last Name"),
            "Academic Year": row.get("School Year"),
            "Semester": semester,
            "Course Code": course_code,
            "Course Title": row.get("Course Title"),
            "Grade Earned": grade,
            "Credit Earned": weight_info["Credit"] / 2,  # Half credit per semester
            "CORE": weight_info["CORE"],
            "Weight": weight_info["Weight"],
            "School": "Keswick Christian School",
            "Source": "Regular"
        }
        merged_records.append(record)
    
    # Process transfer grades
    for _, row in transfer_df.iterrows():
        course_code = str(row.get("Course Code", "")).strip()
        weight_info = weight_lookup.get(course_code, {"CORE": "No", "Weight": 0.0, "Credit": 1.0})
        
        # Skip blank grades
        grade = str(row.get("Grade", "")).strip()
        if not grade or grade.lower() in ["nan", ""]:
            continue
        
        # Transfer grades might have numeric grades like "75" - keep them
        credits_attempted = float(row.get("Credits Attempted", 0.5))
        school_name = row.get("Transfer School Name", "Transfer School")
        
        record = {
            "User ID": row.get("User ID"),
            "First Name": row.get("First Name"),
            "Last Name": row.get("Last Name"),
            "Academic Year": row.get("School Year"),
            "Semester": 1,  # Transfer grades typically don't have semester breakdown
            "Course Code": course_code,
            "Course Title": row.get("Course Title"),
            "Grade Earned": grade,
            "Credit Earned": credits_attempted,
            "CORE": weight_info["CORE"],
            "Weight": weight_info["Weight"],
            "School": school_name,
            "Source": "Transfer"
        }
        merged_records.append(record)
    
    # Create merged dataframe
    merged_df = pd.DataFrame(merged_records)
    
    # Sort by User ID, Academic Year, Semester
    merged_df = merged_df.sort_values(["User ID", "Academic Year", "Semester", "Course Code"])
    
    # Save
    output_path = data_dir / "Merged_Grades.csv"
    merged_df.to_csv(output_path, index=False)
    
    print(f"\n✅ Created Merged_Grades.csv")
    print(f"   Total records: {len(merged_df):,}")
    print(f"   Regular grades: {len(merged_df[merged_df['Source'] == 'Regular']):,}")
    print(f"   Transfer grades: {len(merged_df[merged_df['Source'] == 'Transfer']):,}")
    print(f"   Unique students: {merged_df['User ID'].nunique()}")
    print(f"   CORE courses: {len(merged_df[merged_df['CORE'] == 'Yes']):,}")
    print(f"   Saved to: {output_path}")
    
    return True


if __name__ == "__main__":
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    success = create_merged_grades(data_dir)
    sys.exit(0 if success else 1)
