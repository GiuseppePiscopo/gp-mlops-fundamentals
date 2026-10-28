#!/usr/bin/env bash
# Wait for an Azure ML job to finish and fail unless it completes.
#
# Usage:
#     bash tools/wait-for-job.sh <JOB_NAME> [POLL_SECONDS]
set -euo pipefail

JOB_NAME=${1:?Usage: wait-for-job.sh <JOB_NAME> [POLL_SECONDS]}
POLL_SECONDS=${2:-30}

while true; do
  # a failed status query is treated as transient: the caller's timeout bounds the wait
  STATUS=$(az ml job show --name "$JOB_NAME" --query status -o tsv) || STATUS=Unknown
  echo "$(date -u +%H:%M:%S) $JOB_NAME: $STATUS"
  case "$STATUS" in
    Completed) exit 0 ;;
    Failed | Canceled | NotResponding)
      echo "Job $JOB_NAME ended with status $STATUS" >&2
      exit 1
      ;;
  esac
  sleep "$POLL_SECONDS"
done
