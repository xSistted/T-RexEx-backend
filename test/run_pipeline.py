import csv
import os
import sys

# Ensure the root directory is in sys.path so we can import 'app'
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from app.api.v1.routes.mask import mask
from app.schemas.mask import MaskRequest

# File paths
INPUT_CSV = os.path.join(ROOT_DIR, "test", "data", "pdpa_masking_test_cases.csv")
OUTPUT_CSV = os.path.join(ROOT_DIR, "test", "data", "result.csv")

def run_test_pipeline():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: Could not find {INPUT_CSV}")
        return

    results = []
    total_tests = 0
    passed_tests = 0

    print(f"Running tests from {INPUT_CSV}...\n")

    with open(INPUT_CSV, mode="r", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        
        for row in reader:
            test_id = row.get("id", "N/A")
            description = row.get("description", "")
            notes = row.get("notes", "")
            test_input = row.get("input", "")
            expected = row.get("expected_output", "")
            alt_expected = row.get("alt_expected_output", "")
            
            # Construct the request
            request = MaskRequest(text=test_input)
            
            try:
                # Call the masking function directly
                response = mask(request)
                actual_output = response.masked_text
                
                # Check if the output matches expected or alt expected
                if actual_output == expected or (alt_expected and actual_output == alt_expected):
                    status = "Pass"
                    passed_tests += 1
                else:
                    status = "Fail"
                    
            except Exception as e:
                actual_output = f"ERROR: {str(e)}"
                status = "Error"
                
            total_tests += 1
            
            # Display expected output based on whether alt_expected exists
            if alt_expected:
                expected_display = f"{expected} OR {alt_expected}"
            else:
                expected_display = expected

            # Save the result for this test case
            results.append({
                "id": test_id,
                "status": status,
                "description": description,
                "input": test_input,
                "expected": expected_display,
                "actual": actual_output,
                "notes": notes
            })

    # Write the results to result.csv
    with open(OUTPUT_CSV, mode="w", encoding="utf-8", newline="") as outfile:
        fieldnames = ["id", "status", "description", "input", "expected", "actual", "notes"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(results)

    # Print Summary
    if total_tests > 0:
        pass_rate = (passed_tests / total_tests) * 100
        print(f"--- Test Summary ---")
        print(f"Total Tests : {total_tests}")
        print(f"Passed      : {passed_tests}")
        print(f"Failed      : {total_tests - passed_tests}")
        print(f"Pass Rate   : {pass_rate:.2f}%")
        print(f"Results saved to: {OUTPUT_CSV}")
    else:
        print("No tests found in the CSV.")

if __name__ == "__main__":
    run_test_pipeline()
