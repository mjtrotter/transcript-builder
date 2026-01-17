import pandas as pd
from pathlib import Path

def check_titles():
    p = Path("/Users/mjtrotter/SDK-1/apps/education/transcript-builder/data/Grades.csv")
    df = pd.read_csv(p, encoding="utf-8-sig")
    
    # Filter for Chemistry
    chem = df[df["Course Title"].str.contains("Chemistry", na=False)]
    
    # Get distinct titles
    titles = chem["Course Title"].unique()
    
    print("Distinct Chemistry Titles (REPR mode):")
    import re
    honors_pattern = r'\s+(\(H\)|H|Honors)$'
    for t in titles:
        # Check replacement
        cleaned = re.sub(honors_pattern, "", t)
        match = bool(re.search(honors_pattern, t))
        print(f"'{t}' -> Cleaned: '{cleaned}' | Matches Regex: {match}")

if __name__ == "__main__":
    check_titles()
