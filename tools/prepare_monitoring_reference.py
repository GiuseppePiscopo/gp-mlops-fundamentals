"""Materialize the drift reference for model monitoring: the training split re-encoded
exactly as the registered model consumes it (Date dropped, categoricals one-hot encoded),
as MLTable-ready files.

Usage:
    python tools/prepare_monitoring_reference.py
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from common.training_utils import get_data, prepare_dataframe  # noqa: E402

SOURCE_CSV = "data/sample/SeoulBikeData.csv"
REFERENCE_DIR = "data/monitoring-reference"
MLTABLE_TEMPLATE = os.path.join(os.path.dirname(__file__), "..", "config", "mltable-template", "MLTable")


def main():
    df = get_data(SOURCE_CSV)
    train_df, _ = prepare_dataframe(df)

    os.makedirs(REFERENCE_DIR, exist_ok=True)
    train_df.to_csv(f"{REFERENCE_DIR}/data.csv", index=False)
    shutil.copy(MLTABLE_TEMPLATE, f"{REFERENCE_DIR}/MLTable")
    print(f"Wrote {len(train_df)} rows to {REFERENCE_DIR}/data.csv")


if __name__ == "__main__":
    main()
