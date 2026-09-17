"""Recreate the exact train/test split used by the registered model, as MLTable-ready CSVs
for the Responsible AI dashboard (which requires separate train/test datasets).

Usage:
    python tools/prepare_rai_data.py
"""

import os
import shutil
import sys

import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from common.training_utils import CATEGORICAL_COLUMNS, DROP_COLUMNS, RANDOM_SEED, TARGET_COLUMN, get_data  # noqa: E402

SOURCE_CSV = "data/sample/SeoulBikeData.csv"
TRAIN_DIR = "data/rai-train"
TEST_DIR = "data/rai-test"
MLTABLE_TEMPLATE = os.path.join(os.path.dirname(__file__), "..", "config", "rai-mltable-template", "MLTable")
# the RAI component passes target_column_name as a CLI arg without quoting, so spaces break its argparse
RAI_TARGET_COLUMN = "Rented_Bike_Count"


def prepare_data(df):
    df = df.drop(columns=DROP_COLUMNS)
    df = df.rename(columns={TARGET_COLUMN: RAI_TARGET_COLUMN})
    # same encoding the model was trained on, so RAI can call model.predict() on these rows directly
    df = pd.get_dummies(df, columns=CATEGORICAL_COLUMNS, drop_first=True)

    # same random_state/test_size as common.training_utils.prepare_data, kept as a DataFrame
    # (prepare_data returns numpy arrays, which would lose the column names the RAI dashboard needs)
    train_df, test_df = train_test_split(df, test_size=0.20, random_state=RANDOM_SEED)
    return train_df, test_df


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
