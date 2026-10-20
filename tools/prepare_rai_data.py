"""Recreate the exact train/test split used by the registered model, as MLTable-ready CSVs
for the Responsible AI dashboard (which requires separate train/test datasets).

Usage:
    python tools/prepare_rai_data.py
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from common.training_utils import get_data, prepare_dataframe  # noqa: E402

SOURCE_CSV = "data/sample/SeoulBikeData.csv"
TRAIN_DIR = "data/rai-train"
TEST_DIR = "data/rai-test"
MLTABLE_TEMPLATE = os.path.join(os.path.dirname(__file__), "..", "config", "mltable-template", "MLTable")
# the RAI component passes target_column_name as a CLI arg without quoting, so spaces break its argparse
RAI_TARGET_COLUMN = "Rented_Bike_Count"


def prepare_data(df):
    # the RAI target rename must happen before the split, same as the model's encoding
    return prepare_dataframe(df, rename_target=RAI_TARGET_COLUMN)


def save_split(directory, split_df):
    os.makedirs(directory, exist_ok=True)
    split_df.to_csv(f"{directory}/data.csv", index=False)
    shutil.copy(MLTABLE_TEMPLATE, f"{directory}/MLTable")
    print(f"Wrote {len(split_df)} rows to {directory}/data.csv")


def main():
    df = get_data(SOURCE_CSV)
    train_df, test_df = prepare_data(df)

    save_split(TRAIN_DIR, train_df)
    save_split(TEST_DIR, test_df)


if __name__ == "__main__":
    main()
