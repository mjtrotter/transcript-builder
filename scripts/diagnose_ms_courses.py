import pandas as pd
from pathlib import Path
import re

def end_year_from_str(sy):
    # expect "2021 - 2022"
    # remove spaces
    sy = sy.replace(" ", "")
    parts = sy.split("-")
    if len(parts) >= 2:
        return int(parts[1])
    return 0

def diagnose():
    p = Path("/Users/mjtrotter/SDK-1/apps/education/transcript-builder/data/Grades.csv")
    df = pd.read_csv(p, encoding="utf-8-sig")
    
    # We need Grad Year to calc grade level
    # But grades.csv has "Grad Year" column
    
    df = df.dropna(subset=["Grad Year"])
    ms_courses = []
    
    for _, row in df.iterrows():
        grad_year = int(row["Grad Year"])
        school_year = row["School Year"]
        end_year = end_year_from_str(school_year)
        
        grade_level = 12 - (grad_year - end_year)
        
        if grade_level < 9:
            ms_courses.append(row["Course Title"])
            
    unique_ms = sorted(list(set(ms_courses)))
    
    print(f"Found {len(unique_ms)} unique Middle School (Grade < 9) titles:")
    
    ms_hs_keywords = [
        "algebra",
        "geometry",
        "physical science",
        "spanish",
        "french",
        "latin",
    ]
    
    ms_honors_keywords = [
        "algebra",
        "geometry",
        "biology",
        "chemistry",
        "physics",
        "physical science",
        "pre-calculus",
        "calculus"
    ]
    
    for t in unique_ms:
        lower = t.lower()
        is_hs_credit = any(k in lower for k in ms_hs_keywords)
        is_honors = any(k in lower for k in ms_honors_keywords)
        
        status = []
        if is_hs_credit: status.append("HS_CREDIT")
        if is_honors: status.append("HONORS_FORCE")
        
        print(f"'{t}' -> {status}")

if __name__ == "__main__":
    diagnose()
