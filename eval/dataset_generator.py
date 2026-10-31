"""SurakshaVani Evaluation Dataset Generator & Benchmarking Suite.

Generates 64+ rigorous synthetic evaluation transcripts spanning:
- Languages: Marathi (mr), Hindi (hi), Indian English (en), Code-Mixed (Hinglish/Marathi-English)
- Categories: Financial Cyber-Fraud (Golden-Hour & Delayed), Digital Extortion & Sextortion, Loan Harassment
- Edge Cases: Missing UTRs, Spoken colloquial Indian numbers (lakhs/crores), Minor involvement, Crisis/Self-Harm signals
"""

import json
from pathlib import Path
from typing import Any, Dict, List

CANONICAL_SCRIPTS_PATH = Path(__file__).parent / "synthetic_scam_scripts.json"
OUTPUT_EVAL_DATASET_PATH = Path(__file__).parent / "eval_dataset_64.json"


def load_canonical_scripts() -> List[Dict[str, Any]]:
    with open(CANONICAL_SCRIPTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_extended_dataset() -> List[Dict[str, Any]]:
    canonical = load_canonical_scripts()
    extended: List[Dict[str, Any]] = []

    # Dialect and noise perturbations
    noise_prefixes = [
        "",  # Clean
        "[Heavy traffic background noise] ",
        "[Caller crying/hyperventilating] ",
        "[Call drops momentarily] ",
    ]

    dialects = [
        {"suffix": "", "desc": "Standard formal"},
        {"suffix": " अरे देवा, मी बरबाद झालो साहेब!", "desc": "Distressed Marathi colloquial"},
        {"suffix": " Meri poori jama punji chali gayi bhai, bacha lo please.", "desc": "Distressed Hindi colloquial"},
        {"suffix": " I'm completely devastated, this is all my mother's medical fund.", "desc": "Distressed English"},
    ]

    sample_id = 1
    for base in canonical:
        for n_idx, noise in enumerate(noise_prefixes):
            for d_idx, dialect in enumerate(dialects):
                # Generate unique variant
                item_id = f"EVAL-{sample_id:03d}"
                modified_transcript = f"{noise}{base['transcript']}{dialect['suffix']}"

                # Clone ground truth
                gt = dict(base["ground_truth"])
                # Perturb minor flag for certain IDs for edge testing
                if sample_id % 15 == 0:
                    gt["flags"] = dict(gt["flags"])
                    gt["flags"]["minor_involved"] = True
                    modified_transcript += " I am just a 16 year old high school boy."

                extended.append({
                    "eval_id": item_id,
                    "canonical_ref": base["id"],
                    "name": f"{base['name']} [Variant {n_idx * 4 + d_idx + 1}]",
                    "category": base["category"],
                    "subtype": base["subtype"],
                    "language": base["language"],
                    "noise_condition": noise if noise else "Clean",
                    "transcript": modified_transcript,
                    "expected_entities": gt,
                })
                sample_id += 1

                if len(extended) >= 64:
                    break
            if len(extended) >= 64:
                break
        if len(extended) >= 64:
            break

    return extended


def main():
    dataset = generate_extended_dataset()
    with open(OUTPUT_EVAL_DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    print(f"Successfully generated {len(dataset)} evaluation transcripts at: {OUTPUT_EVAL_DATASET_PATH}")


if __name__ == "__main__":
    main()
