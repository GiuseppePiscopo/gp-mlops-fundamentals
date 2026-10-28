"""Evaluation gate for the CI/CD workflow: fail unless a finished training job meets the quality thresholds.

Reads the metrics that the training job logged to MLflow in the Azure ML workspace
(run id == job name) and exits with a non-zero code when the gate fails.

Usage:
    python tools/evaluate.py --job_name <JOB_NAME> [--min_r2 0.80] [--max_rmse 300]
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time

import mlflow

AZ = shutil.which("az") or "az"
TRANSIENT_ERRORS = ("ConnectionResetError", "10054", "Connection aborted", "Max retries exceeded")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job_name", required=True, type=str)
    parser.add_argument("--min_r2", type=float, default=0.80)
    parser.add_argument("--max_rmse", type=float, default=300.0)
    return parser.parse_args()


def is_transient(stderr):
    return any(marker in stderr for marker in TRANSIENT_ERRORS)


def run_az(args):
    last = None
    for _ in range(5):
        last = subprocess.run(
            [AZ, *args, "--only-show-errors"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if last.returncode == 0:
            return last
        if not is_transient(last.stderr):
            break
        time.sleep(2)
    sys.exit(f"az {' '.join(args)} failed: {last.stderr.strip()}")


def get_tracking_uri():
    return run_az(["ml", "workspace", "show", "--query", "mlflow_tracking_uri", "-o", "tsv"]).stdout.strip()


def write_summary(lines):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write("\n".join(lines) + "\n")


def main(args):
    mlflow.set_tracking_uri(get_tracking_uri())
    run = mlflow.get_run(args.job_name)

    print(f"\n=== Evaluation gate for job {args.job_name} ===")
    if run.info.status != "FINISHED":
        sys.exit(f"GATE FAILED: job {args.job_name} status is {run.info.status}, expected FINISHED")

    r2 = run.data.metrics["R2"]
    rmse = run.data.metrics["RMSE"]
    checks = [
        ("R2", r2, f">= {args.min_r2}", r2 >= args.min_r2),
        ("RMSE", rmse, f"<= {args.max_rmse}", rmse <= args.max_rmse),
    ]

    summary = [
        f"### Evaluation gate for `{args.job_name}`",
        "",
        "| Metric | Value | Threshold | Result |",
        "|---|---|---|---|",
    ]
    for name, value, threshold, passed in checks:
        result = "PASS" if passed else "FAIL"
        print(f"{name}: {value:.4f} (required {threshold}) -> {result}")
        summary.append(f"| {name} | {value:.4f} | {threshold} | {result} |")
    write_summary(summary)

    if not all(passed for *_, passed in checks):
        sys.exit("GATE FAILED: the model does not meet the quality thresholds")
    print("GATE PASSED")


if __name__ == "__main__":
    # keep stdout and stderr in execution order when piped (CI logs)
    sys.stdout.reconfigure(line_buffering=True)
    # label SDK warnings with their logger, so they aren't mistaken for errors of this script
    logging.basicConfig(format="[%(name)s] %(levelname)s: %(message)s")
    main(parse_args())
