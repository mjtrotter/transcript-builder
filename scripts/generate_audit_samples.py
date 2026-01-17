import pandas as pd
import sys
import os
import random
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src"))

from transcript_generator import TranscriptGenerator

def generate_samples():
    output_dir = Path.home() / "Desktop" / "Transcript_Test_Sample" / "Audit_Samples"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = project_root / "output" / "layout_audit_results.csv"
    if not csv_path.exists():
        print("CSV not found!")
        return

    df = pd.read_csv(csv_path)
    
    # High Risk
    high_risk_ids = df[df["Risk"] == "High"]["User ID"].tolist()
    # Ensure they are ints
    high_risk_ids = [int(x) for x in high_risk_ids]
    # Manually add Elliana Aldrich for Honors Test
    # Manually add Samuel Ross for Chemistry I H Test (4021436)
    # for uid in [7414206, 4021436]:
    #    if uid not in high_risk_ids:
    #        high_risk_ids.append(uid)
    
    # Monitor
    monitor_ids = df[df["Risk"] == "Monitor"]["User ID"].tolist()
    monitor_ids = [int(x) for x in monitor_ids]
    
    monitor_ids = df[df["Risk"] == "Monitor"]["User ID"].tolist()
    monitor_ids = [int(x) for x in monitor_ids]
    
    # Include key test cases for transfer & honors validation
    import random
    sample_monitor = random.sample(monitor_ids, min(5, len(monitor_ids)))
    # 6541335 = Raven (MS Transfer Algebra 1), 5697361 = Jaylen (HS Transfer)
    target_ids = list(set(high_risk_ids + sample_monitor + [6541335, 5697361]))
    
    print(f"Generating {len(target_ids)} samples...")
    print(f"  High Risk: {high_risk_ids}")
    
    from gpa_calculator import GPACalculator
    from class_rank_calculator import ClassRankCalculator
    from data_models import CourseWeight

    generator = TranscriptGenerator()
    print("Loading data...")
    if not generator.data_processor.load_all_data():
        print("Failed to load data")
        return

    # Initialize GPA Calculator
    # Convert DataFrame to Dict[str, CourseWeight]
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
    
    # Populate Rankings
    # Extract (user_id, weighted_gpa) from gpa_results
    student_gpas = []
    for uid, gpa_res in generator.data_processor.gpa_results.items():
        # Using CORE weighted GPA for ranking (standard)
        student_gpas.append((uid, gpa_res.core_weighted_gpa))
        
    generator.rank_calculator.calculate_class_rankings(student_gpas)
    
    for uid in target_ids:
        print(f"Generating {uid}...")
        try:
            # We want to output to our specific sample dir
            # The generator usually saves to project/output or Desktop/Transcript_Test_Sample
            # We might need to move it or configure output path if possible.
            # Generator.generate_transcript returns the path.
            
            pdf_path = generator.generate_transcript(uid, layout="minimalist")
            if pdf_path:
                # Move/Copy to sample dir
                dest = output_dir / pdf_path.name
                # Use shutil
                import shutil
                shutil.copy2(pdf_path, dest)
                print(f"  -> Saved to {dest}")
        except Exception as e:
            print(f"  Failed {uid}: {e}")

    print(f"\nDone. Files in {output_dir}")

if __name__ == "__main__":
    generate_samples()
