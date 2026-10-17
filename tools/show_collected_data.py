"""Inspect the production data logged by the endpoint data collector.

Reads the JSON Lines files that the data collector writes to the workspace's
default datastore (``modelDataCollector/{endpoint}/{deployment}/{collection}/``)
and prints a short summary plus the first few recorded requests, so you can
confirm that data collection is working even before a monitor reads the data.

Usage:
    python tools/show_collected_data.py
    python tools/show_collected_data.py --deployment green --collection model_outputs
    python tools/show_collected_data.py --deployment blue --show 5
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

AZ = shutil.which("az") or "az"
TRANSIENT_ERRORS = ("ConnectionResetError", "10054", "Connection aborted", "Max retries exceeded")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="gp-mof-capstone-endpoint")
    parser.add_argument("--deployment", default="blue")
    parser.add_argument("--collection", default="model_inputs")
    parser.add_argument("--datastore", default="workspaceblobstore")
    parser.add_argument("--show", type=int, default=3, help="Number of records to print.")
    args = parser.parse_args()
    return args


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
    print(last.stderr.strip(), file=sys.stderr)
    sys.exit(1)


def run_az_json(args):
    return json.loads(run_az([*args, "-o", "json"]).stdout)


def get_storage_coordinates(datastore):
    info = run_az_json(["ml", "datastore", "show", "--name", datastore])
    return info["account_name"], info["container_name"]


def list_blobs(account, container, prefix):
    blobs = run_az_json(
        [
            "storage",
            "blob",
            "list",
            "--account-name",
            account,
            "--container-name",
            container,
            "--prefix",
            prefix,
        ]
    )
    jsonl = [b for b in blobs if b["name"].endswith(".jsonl")]
    jsonl.sort(key=lambda b: b["properties"]["lastModified"], reverse=True)
    return jsonl


def download_blob(account, container, name):
    tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    tmp.close()
    try:
        run_az(
            [
                "storage",
                "blob",
                "download",
                "--account-name",
                account,
                "--container-name",
                container,
                "--name",
                name,
                "--file",
                tmp.name,
                "--no-progress",
            ]
        )
    except SystemExit:
        Path(tmp.name).unlink(missing_ok=True)
        raise
    return tmp.name


def get_records(account, container, name):
    local = download_blob(account, container, name)
    try:
        text = Path(local).read_text(encoding="utf-8")
    finally:
        Path(local).unlink(missing_ok=True)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def main():
    args = parse_args()
    prefix = f"modelDataCollector/{args.endpoint}/{args.deployment}/{args.collection}/"

    account, container = get_storage_coordinates(args.datastore)
    print(f"Collection: {args.collection}")
    print(f"Location:   {args.datastore}/{prefix}")

    blobs = list_blobs(account, container, prefix)
    if not blobs:
        print("\nNo collected data yet. Data appears a few minutes after the first request, and")
        print("each file is written once the rolling window rolls over (rolling_rate in the")
        print("deployment YAML). Send some requests, wait, and run this again.")
        return

    print(f"Files:      {len(blobs)}")

    records = get_records(account, container, blobs[0]["name"])

    print(f"Latest:     {blobs[0]['name']}")
    print(f"Records:    {len(records)} in the latest file")

    print(f"\nFirst {min(args.show, len(records))} recorded request(s):")
    for record in records[: args.show]:
        print(f"\n- time={record.get('time')} type={record.get('type')} model.version={record.get('modelversion')}")
        print(f"  data={json.dumps(record.get('data'), ensure_ascii=False)}")


if __name__ == "__main__":
    main()
