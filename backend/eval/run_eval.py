"""Eval Harness — runs the full AI Debugging Agent against curated test cases.

Usage:
    cd backend
    source venv/bin/activate
    python -m eval.run_eval           # Full run (requires API keys)
    python -m eval.run_eval --dry-run # Dry run (validates cases, no LLM calls)

Requires: GROQ_API_KEY and/or GEMINI_API_KEY in .env
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.error_parser import parse_error
from agent.orchestrator import run_debug_session, resume_session
from parsers.models import DebugResult


# Configuration
CASES_DIR = Path(__file__).parent / "cases"
RESULTS_FILE = Path(__file__).parent / "EVAL_RESULTS.md"
TIMEOUT_PER_CASE = 90  # seconds
MAX_RETRIES_ON_RATE_LIMIT = 2
RATE_LIMIT_WAIT = 60  # seconds


def load_cases() -> List[dict]:
    """Load all test cases from the cases/ directory."""
    cases = []
    for f in sorted(CASES_DIR.glob("*.json")):
        with open(f) as fp:
            case = json.load(fp)
            cases.append(case)
    return cases


def check_accuracy(result: DebugResult, ground_truth: dict) -> bool:
    """Check if the agent's conclusion matches ground truth keywords.

    Case-insensitive. Any keyword appearing in conclusion OR suggested_fix
    counts as a match.
    """
    keywords = ground_truth.get("keywords", [])
    if not keywords:
        return False

    # Combine conclusion and suggested_fix for matching
    agent_output = (result.conclusion + " " + result.suggested_fix).lower()

    for keyword in keywords:
        if keyword.lower() in agent_output:
            return True

    return False


async def run_single_case(case: dict) -> dict:
    """Run the agent on a single test case. Returns result dict."""
    case_id = case["id"]
    start_time = time.time()

    try:
        # Parse the error
        error_context = parse_error(case["traceback"], case["buggy_code"])

        # Run the full debug session
        result = await asyncio.wait_for(
            run_debug_session(error_context, case["buggy_code"]),
            timeout=TIMEOUT_PER_CASE,
        )

        elapsed = time.time() - start_time

        # Handle pending question (auto-answer "I don't know")
        if isinstance(result, dict) and result.get("status") == "pending_question":
            session_id = result["session_id"]
            result = await asyncio.wait_for(
                resume_session(session_id, "I don't know"),
                timeout=TIMEOUT_PER_CASE,
            )
            elapsed = time.time() - start_time

            # If still pending, answer again (max 3 questions)
            retries = 0
            while isinstance(result, dict) and result.get("status") == "pending_question" and retries < 3:
                session_id = result["session_id"]
                result = await asyncio.wait_for(
                    resume_session(session_id, "I don't have that information"),
                    timeout=TIMEOUT_PER_CASE,
                )
                retries += 1
                elapsed = time.time() - start_time

        # Check if we got an error dict
        if isinstance(result, dict):
            if "error" in result:
                return {
                    "case_id": case_id,
                    "category": case["category"],
                    "status": "error",
                    "error": result["error"],
                    "elapsed": elapsed,
                    "correct": False,
                    "confidence": 0.0,
                    "iterations": 0,
                    "conclusion": "",
                }
            # Still pending — shouldn't happen but handle gracefully
            return {
                "case_id": case_id,
                "category": case["category"],
                "status": "incomplete",
                "error": "Session did not conclude",
                "elapsed": elapsed,
                "correct": False,
                "confidence": 0.0,
                "iterations": 0,
                "conclusion": "",
            }

        # We have a DebugResult
        correct = check_accuracy(result, case["ground_truth"])
        iterations = len([r for r in result.reasoning_chain if "Iteration" in r and "Thought" in r])

        return {
            "case_id": case_id,
            "category": case["category"],
            "status": "completed",
            "correct": correct,
            "confidence": result.confidence,
            "confidence_level": result.confidence_level,
            "iterations": iterations,
            "elapsed": elapsed,
            "conclusion": result.conclusion[:200],
            "suggested_fix": result.suggested_fix[:200] if result.suggested_fix else "",
        }

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        return {
            "case_id": case_id,
            "category": case["category"],
            "status": "timeout",
            "error": f"Timed out after {TIMEOUT_PER_CASE}s",
            "elapsed": elapsed,
            "correct": False,
            "confidence": 0.0,
            "iterations": 0,
            "conclusion": "",
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "case_id": case_id,
            "category": case["category"],
            "status": "error",
            "error": str(e),
            "elapsed": elapsed,
            "correct": False,
            "confidence": 0.0,
            "iterations": 0,
            "conclusion": "",
        }


async def run_eval(dry_run: bool = False):
    """Run the full evaluation."""
    cases = load_cases()
    print(f"Loaded {len(cases)} test cases from {CASES_DIR}")
    print()

    if dry_run:
        print("=== DRY RUN MODE (no LLM calls) ===")
        print()
        _dry_run_validate(cases)
        return

    # Check for API keys
    from dotenv import load_dotenv
    load_dotenv()
    if not os.getenv("GROQ_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        print("ERROR: No API keys found in .env")
        print("Set GROQ_API_KEY and/or GEMINI_API_KEY to run eval.")
        sys.exit(1)

    print(f"=== Running Eval ({len(cases)} cases) ===")
    print(f"Timeout per case: {TIMEOUT_PER_CASE}s")
    print()

    results = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] Running: {case['id']} ({case['category']})...", end=" ", flush=True)

        # Rate limit handling with retry
        for attempt in range(MAX_RETRIES_ON_RATE_LIMIT + 1):
            result = await run_single_case(case)

            if result["status"] == "error" and "rate" in result.get("error", "").lower():
                if attempt < MAX_RETRIES_ON_RATE_LIMIT:
                    print(f"\n  Rate limited. Waiting {RATE_LIMIT_WAIT}s...", end=" ", flush=True)
                    await asyncio.sleep(RATE_LIMIT_WAIT)
                    continue
            break

        results.append(result)

        # Print result
        status_icon = "✅" if result["correct"] else ("⚠️" if result["status"] != "completed" else "❌")
        print(f"{status_icon} ({result['elapsed']:.1f}s, conf={result['confidence']:.2f})")

        # Small delay between cases to avoid rate limits
        if i < len(cases):
            await asyncio.sleep(2)

    print()
    print("=" * 50)

    # Compute and display metrics
    metrics = compute_metrics(results)
    display_metrics(metrics, results)

    # Write results file
    write_results_md(metrics, results)
    print(f"\nResults written to: {RESULTS_FILE}")


def compute_metrics(results: List[dict]) -> dict:
    """Compute aggregate metrics from results."""
    completed = [r for r in results if r["status"] == "completed"]
    errors = [r for r in results if r["status"] in ("error", "timeout", "incomplete")]

    total = len(results)
    correct = sum(1 for r in completed if r["correct"])
    accuracy = (correct / len(completed) * 100) if completed else 0

    avg_iterations = (sum(r["iterations"] for r in completed) / len(completed)) if completed else 0
    avg_confidence = (sum(r["confidence"] for r in completed) / len(completed)) if completed else 0
    avg_time = (sum(r["elapsed"] for r in results) / len(results)) if results else 0

    # Confidence calibration
    high_conf = [r for r in completed if r["confidence"] >= 0.70]
    low_conf = [r for r in completed if r["confidence"] < 0.70]
    high_conf_accuracy = (sum(1 for r in high_conf if r["correct"]) / len(high_conf) * 100) if high_conf else 0
    low_conf_accuracy = (sum(1 for r in low_conf if r["correct"]) / len(low_conf) * 100) if low_conf else 0

    # Category breakdown
    categories = {}
    for r in completed:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "correct": 0}
        categories[cat]["total"] += 1
        if r["correct"]:
            categories[cat]["correct"] += 1

    return {
        "total": total,
        "completed": len(completed),
        "errors": len(errors),
        "correct": correct,
        "accuracy": accuracy,
        "avg_iterations": avg_iterations,
        "avg_confidence": avg_confidence,
        "avg_time": avg_time,
        "high_conf_count": len(high_conf),
        "high_conf_correct": sum(1 for r in high_conf if r["correct"]),
        "high_conf_accuracy": high_conf_accuracy,
        "low_conf_count": len(low_conf),
        "low_conf_correct": sum(1 for r in low_conf if r["correct"]),
        "low_conf_accuracy": low_conf_accuracy,
        "categories": categories,
    }


def display_metrics(metrics: dict, results: List[dict]):
    """Display metrics to console."""
    print(f"\n{'='*50}")
    print(f"EVAL RESULTS SUMMARY")
    print(f"{'='*50}")
    print(f"Total cases:     {metrics['total']}")
    print(f"Completed:       {metrics['completed']}")
    print(f"Errors/Timeouts: {metrics['errors']}")
    print(f"Correct:         {metrics['correct']}/{metrics['completed']}")
    print(f"Accuracy:        {metrics['accuracy']:.1f}%")
    print(f"Avg Iterations:  {metrics['avg_iterations']:.1f}")
    print(f"Avg Confidence:  {metrics['avg_confidence']:.2f}")
    print(f"Avg Time:        {metrics['avg_time']:.1f}s")
    print()
    print("Confidence Calibration:")
    print(f"  High (>=0.70): {metrics['high_conf_correct']}/{metrics['high_conf_count']} = {metrics['high_conf_accuracy']:.1f}%")
    print(f"  Low  (<0.70):  {metrics['low_conf_correct']}/{metrics['low_conf_count']} = {metrics['low_conf_accuracy']:.1f}%")
    print()
    print("Category Breakdown:")
    for cat, data in sorted(metrics["categories"].items()):
        acc = (data["correct"] / data["total"] * 100) if data["total"] else 0
        print(f"  {cat:20s}: {data['correct']}/{data['total']} = {acc:.0f}%")

    # Show failures
    failures = [r for r in results if r["status"] == "completed" and not r["correct"]]
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for f in failures:
            print(f"  - {f['case_id']}: {f['conclusion'][:80]}...")


def write_results_md(metrics: dict, results: List[dict]):
    """Write EVAL_RESULTS.md with full results table."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# Eval Results — AI Debugging Agent",
        "",
        f"Run date: {now}",
        "Model: llama-3.3-70b-versatile (Groq) + gemini-2.0-flash (fallback)",
        f"Total cases: {metrics['total']}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Accuracy | {metrics['accuracy']:.1f}% ({metrics['correct']}/{metrics['completed']} correct) |",
        f"| Avg Iterations | {metrics['avg_iterations']:.1f} |",
        f"| Avg Confidence | {metrics['avg_confidence']:.2f} |",
        f"| Avg Time | {metrics['avg_time']:.1f}s per case |",
        f"| Errors/Timeouts | {metrics['errors']} |",
        "",
        "## Confidence Calibration",
        "",
        "| Confidence Level | Cases | Correct | Accuracy |",
        "|---|---|---|---|",
        f"| High (>=0.70) | {metrics['high_conf_count']} | {metrics['high_conf_correct']} | {metrics['high_conf_accuracy']:.1f}% |",
        f"| Low (<0.70) | {metrics['low_conf_count']} | {metrics['low_conf_correct']} | {metrics['low_conf_accuracy']:.1f}% |",
        "",
        "## Category Breakdown",
        "",
        "| Category | Cases | Correct | Accuracy |",
        "|---|---|---|---|",
    ]

    for cat, data in sorted(metrics["categories"].items()):
        acc = (data["correct"] / data["total"] * 100) if data["total"] else 0
        lines.append(f"| {cat} | {data['total']} | {data['correct']} | {acc:.0f}% |")

    lines += [
        "",
        "## Detailed Results",
        "",
        "| Case | Category | Status | Correct | Confidence | Iterations | Time |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in results:
        icon = "✅" if r["correct"] else ("⚠️" if r["status"] != "completed" else "❌")
        lines.append(
            f"| {r['case_id']} | {r['category']} | {r['status']} | {icon} | "
            f"{r['confidence']:.2f} | {r['iterations']} | {r['elapsed']:.1f}s |"
        )

    # Failures section
    failures = [r for r in results if r["status"] == "completed" and not r["correct"]]
    if failures:
        lines += ["", "## Failures", ""]
        for f in failures:
            lines.append(f"### {f['case_id']}")
            lines.append(f"- **Agent conclusion**: {f['conclusion']}")
            lines.append(f"- **Confidence**: {f['confidence']:.2f}")
            lines.append("")

    # Error section
    error_cases = [r for r in results if r["status"] in ("error", "timeout")]
    if error_cases:
        lines += ["", "## Errors/Timeouts", ""]
        for e in error_cases:
            lines.append(f"- **{e['case_id']}**: {e.get('error', 'unknown error')}")

    lines.append("")
    RESULTS_FILE.write_text("\n".join(lines))


def _dry_run_validate(cases: List[dict]):
    """Validate all cases without making LLM calls."""
    print(f"Validating {len(cases)} test cases...\n")

    all_valid = True
    for case in cases:
        errors = []

        # Required fields
        for field in ["id", "category", "description", "buggy_code", "traceback", "ground_truth"]:
            if field not in case:
                errors.append(f"Missing field: {field}")

        # Ground truth fields
        gt = case.get("ground_truth", {})
        for field in ["root_cause", "error_type", "keywords"]:
            if field not in gt:
                errors.append(f"Missing ground_truth.{field}")

        if not gt.get("keywords"):
            errors.append("ground_truth.keywords is empty")

        # Test error parsing
        from parsers.error_parser import parse_error
        ctx = parse_error(case.get("traceback", ""), case.get("buggy_code", ""))

        # Print status
        if errors:
            print(f"  ❌ {case['id']}: {', '.join(errors)}")
            all_valid = False
        else:
            print(f"  ✅ {case['id']} ({case['category']}, {case.get('difficulty', '?')})")
            print(f"     Parsed: {ctx.error_type} at line {ctx.line_number}")
            print(f"     Keywords: {gt['keywords'][:4]}...")

    print()
    if all_valid:
        print(f"All {len(cases)} cases valid! ✅")
        print("Run without --dry-run to execute with real LLM calls.")
    else:
        print("Some cases have issues. Fix before running eval.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(run_eval(dry_run=dry_run))
