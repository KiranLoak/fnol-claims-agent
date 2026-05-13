"""
main.py

Entry point for the FNOL Claims Processing Agent.

Usage:
    # Process all FNOL files in the sample_fnols/ folder
    python main.py

    # Process a specific file
    python main.py --file sample_fnols/fnol_001.txt

    # Process a specific file and save output
    python main.py --file sample_fnols/fnol_002.txt --save

    # Process all files and save all outputs
    python main.py --save

I built this as part of an insurance claims automation assignment.
Used Claude (Anthropic) to help with the field extraction — it handles
the messy NLP part of reading unstructured FNOL documents way better than
handwritten parsing rules would.
"""

import os
import json
import argparse
from datetime import datetime

from agent import extract_fields_with_llm, find_missing_fields
from router import determine_route


def load_document(filepath: str) -> str:
    """Reads a text file and returns its contents."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def process_fnol(filepath: str) -> dict:
    """
    Full pipeline for one FNOL document:
    1. Load the file
    2. Extract fields using Claude
    3. Find missing fields
    4. Determine routing
    5. Return the final result as a dict
    """
    print(f"\n{'='*60}")
    print(f"  Processing: {os.path.basename(filepath)}")
    print(f"{'='*60}")

    # step 1: load the document
    doc_text = load_document(filepath)
    print("  [1/3] Document loaded.")

    # step 2: extract fields using Claude API
    print("  [2/3] Extracting fields with Groq (llama-3.1-8b-instant)...")
    extracted = extract_fields_with_llm(doc_text)
    print("        Done.")

    # step 3: find missing fields
    missing = find_missing_fields(extracted)
    if missing:
        print(f"        Missing fields found: {missing}")
    else:
        print("        All mandatory fields present.")

    # step 4: determine routing
    print("  [3/3] Running routing logic...")
    routing = determine_route(extracted, missing)
    print(f"        Route: {routing['recommendedRoute']}")

    # build the final output object
    result = {
        "source_file": os.path.basename(filepath),
        "processed_at": datetime.now().isoformat(),
        "extractedFields": extracted,
        "missingFields": missing,
        "recommendedRoute": routing["recommendedRoute"],
        "reasoning": routing["reasoning"]
    }

    return result


def save_output(result: dict, output_dir: str = "outputs"):
    """Saves the result JSON to the outputs folder."""
    os.makedirs(output_dir, exist_ok=True)
    source_name = result["source_file"].replace(".txt", "").replace(".pdf", "")
    output_path = os.path.join(output_dir, f"{source_name}_result.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Output saved to: {output_path}")
    return output_path


def print_summary(result: dict):
    """Prints a nicely formatted summary of the claim result."""
    print(f"\n{'─'*60}")
    print(f"  CLAIM SUMMARY: {result['source_file']}")
    print(f"{'─'*60}")

    policy = result["extractedFields"].get("policy_information", {})
    incident = result["extractedFields"].get("incident_information", {})
    claim = result["extractedFields"].get("claim_details", {})
    asset = result["extractedFields"].get("asset_details", {})

    print(f"  Policyholder  : {policy.get('policyholder_name', 'N/A')}")
    print(f"  Policy Number : {policy.get('policy_number', 'N/A')}")
    print(f"  Incident Date : {incident.get('date_of_incident', 'N/A')}")
    print(f"  Claim Type    : {claim.get('claim_type', 'N/A')}")
    print(f"  Est. Damage   : {asset.get('estimated_damage', 'N/A')}")

    if result["missingFields"]:
        print(f"\n  ⚠  Missing Fields : {', '.join(result['missingFields'])}")
    else:
        print(f"\n  ✓  All fields present")

    print(f"\n  ➜  Recommended Route : {result['recommendedRoute']}")
    print(f"\n  Reasoning: {result['reasoning']}")
    print(f"{'─'*60}")


def main():
    parser = argparse.ArgumentParser(
        description="FNOL Insurance Claims Processing Agent"
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to a specific FNOL file to process. If not given, processes all files in sample_fnols/"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save output JSON files to the outputs/ directory"
    )
    args = parser.parse_args()

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║      FNOL Autonomous Insurance Claims Processing Agent      ║")
    print("║           Powered by Groq + LLaMA 3.1 (Free!)              ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # figure out which files to process
    if args.file:
        if not os.path.exists(args.file):
            print(f"\n  ERROR: File not found — {args.file}")
            return
        files_to_process = [args.file]
    else:
        sample_dir = "sample_fnols"
        if not os.path.exists(sample_dir):
            print(f"\n  ERROR: No sample_fnols/ directory found. Create it and add FNOL text files.")
            return
        files_to_process = [
            os.path.join(sample_dir, f)
            for f in sorted(os.listdir(sample_dir))
            if f.endswith((".txt", ".pdf"))
        ]
        if not files_to_process:
            print(f"\n  No .txt or .pdf files found in {sample_dir}/")
            return

    print(f"\n  Found {len(files_to_process)} FNOL document(s) to process.")

    all_results = []

    for filepath in files_to_process:
        try:
            result = process_fnol(filepath)
            print_summary(result)
            all_results.append(result)

            if args.save:
                save_output(result)

        except Exception as e:
            print(f"\n  ERROR processing {filepath}: {e}")
            # continue with next file instead of crashing everything
            continue

    # print final summary table
    print(f"\n\n{'='*60}")
    print("  FINAL ROUTING SUMMARY")
    print(f"{'='*60}")
    print(f"  {'File':<20} {'Route':<25} {'Missing Fields'}")
    print(f"  {'-'*58}")
    for r in all_results:
        missing_str = str(len(r["missingFields"])) + " field(s)" if r["missingFields"] else "None"
        print(f"  {r['source_file']:<20} {r['recommendedRoute']:<25} {missing_str}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
