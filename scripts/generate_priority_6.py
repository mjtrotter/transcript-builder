#!/usr/bin/env python3
"""
Generate 6 priority transcripts for immediate upload
"""

import sys
import os
import shutil

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from transcript_generator import TranscriptGenerator
from transcript_data_processor import TranscriptDataProcessor
from gpa_calculator import GPACalculator

# The 6 SENIORS who need transcripts TODAY
PRIORITY_STUDENTS = [
    (4896076, "Maya deVega"),
    (5697361, "Jaylen Doane"),
    (7269654, "Luke Drechsel"),
    (5493311, "Hannah Lamoureux"),
    (4097028, "Landon Pauley-Sherman"),
    (4021503, "Eiley Tacia"),
]


def main():
    print("=" * 80)
    print("🚀 GENERATING 6 PRIORITY TRANSCRIPTS FOR TODAY")
    print("=" * 80)
    print()

    # Initialize data processor
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    processor = TranscriptDataProcessor(data_dir)

    # Initialize GPA calculator
    gpa_calculator = GPACalculator(processor)
    gpa_calculator.calculate_all_gpas()

    # Initialize generator
    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    output_dir = os.path.join(
        os.path.dirname(__file__), "..", "output", "priority_transcripts"
    )

    generator = TranscriptGenerator(
        templates_dir=templates_dir,
        output_dir=output_dir,
        data_processor=processor,
        gpa_calculator=gpa_calculator,
    )

    # Create Desktop output folder
    desktop_dir = os.path.expanduser("~/Desktop/Priority_Transcripts")
    os.makedirs(desktop_dir, exist_ok=True)

    success_count = 0
    failed = []

    for student_id, name in PRIORITY_STUDENTS:
        print(f"📄 Generating: {name} (ID: {student_id})...")

        try:
            # Generate with minimalist layout
            pdf_path = generator.generate_transcript(
                student_id=student_id, transcript_type="Official", layout="minimalist"
            )

            if pdf_path and os.path.exists(pdf_path):
                # Copy to Desktop
                dest = os.path.join(desktop_dir, os.path.basename(pdf_path))
                shutil.copy2(pdf_path, dest)
                print(f"   ✅ Generated: {os.path.basename(pdf_path)}")
                success_count += 1
            else:
                print(f"   ⚠️  PDF not found")
                failed.append(name)

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback

            traceback.print_exc()
            failed.append(name)

        print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully generated: {success_count}/6")
    if failed:
        print(f'❌ Failed: {", ".join(failed)}')
    print()
    print(f"📁 Location: {desktop_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
