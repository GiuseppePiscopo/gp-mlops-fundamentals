"""Send drifted traffic to the production deployment to exercise model monitoring.

Perturbs the pre-processed feature vector away from the training distribution
(hot night hours: Hour ~3, Temperature ~33C, Humidity ~25%) and invokes the
endpoint once per payload, so data collection logs them as production data.

Usage:
    python tools/simulate_drift.py
    python tools/simulate_drift.py --count 50 --endpoint gp-mof-capstone-endpoint --deployment blue
"""

import argparse
import json
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

AZ = shutil.which("az") or "az"
TRANSIENT_ERRORS = ("ConnectionResetError", "10054", "Connection aborted", "Max retries exceeded")
BASE_FILE = Path(__file__).resolve().parent.parent / "data" / "test-request" / "request.json"


def is_transient(stderr):
    return any(marker in stderr for marker in TRANSIENT_ERRORS)


def run_az(cmd):
    last = None
    for _ in range(3):
        last = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if last.returncode == 0:
            return last
        if not is_transient(last.stderr):
            break
        time.sleep(2)
    return last


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--endpoint", default="gp-mof-capstone-endpoint")
    parser.add_argument("--deployment", default="blue")
    parser.add_argument("--base-file", default=str(BASE_FILE))
    args = parser.parse_args()
    return args


def load_base_file(args):
    with open(args.base_file, encoding="utf-8") as f:
        split = json.load(f)["input_data"]
    columns = split["columns"]
    base = dict(zip(columns, split["data"][0]))
    return columns, base


def make_drifted_row(base, rng):
    row = dict(base)
    # training means: Hour ~11.5, Temperature ~12.9C, Humidity ~58%.
    # Drift: heatwave nights, far from the bulk of the training data.
    row["Hour"] = rng.choice([2, 3, 4])
    row["Temperature(°C)"] = round(rng.gauss(33.0, 1.5), 1)
    row["Humidity(%)"] = int(rng.gauss(25, 4))
    return row


def send_drifted_requests(args, columns, base):
    rng = random.Random(42)
    failures = 0
    for i in range(args.count):
        row = make_drifted_row(base, rng)
        payload = {"input_data": {"columns": columns, "index": [0], "data": [[row[c] for c in columns]]}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(payload, tmp)
            tmp_path = tmp.name

        cmd = [
            AZ,
            "ml",
            "online-endpoint",
            "invoke",
            "--name",
            args.endpoint,
            "--deployment-name",
            args.deployment,
            "--request-file",
            tmp_path,
        ]
        result = run_az(cmd)

        Path(tmp_path).unlink(missing_ok=True)

        if result.returncode != 0:
            failures += 1
            last_error = (result.stderr.strip().splitlines() or [""])[-1]
            print(f"[{i + 1}/{args.count}] failed: {last_error}")
        elif (i + 1) % 10 == 0 or i == 0:
            print(f"[{i + 1}/{args.count}] ok: {result.stdout.strip()[:120]}")

    print(f"Done: {args.count - failures}/{args.count} drifted requests sent.")
    return failures


def main():
    args = parse_args()

    columns, base = load_base_file(args)

    failures = send_drifted_requests(args, columns, base)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
