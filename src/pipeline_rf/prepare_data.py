import argparse
import glob
import os

import pandas as pd

TARGET_COLUMN = "Rented Bike Count"
CATEGORICAL_COLUMNS = ["Seasons", "Holiday", "Functioning Day"]
DROP_COLUMNS = ["Date"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_data", dest="input_data", type=str)
    parser.add_argument("--output_data", dest="output_data", type=str)
    return parser.parse_args()


def get_data(path):
    print("Reading data...")

    csv_files = glob.glob(os.path.join(path, "*.csv"))
    if not csv_files:
        raise RuntimeError(f"No CSV files found in provided data path: {path}")
    df = pd.concat((pd.read_csv(f) for f in csv_files), ignore_index=True)

    return df


def prepare_data(df):
    print("Preparing data...")

    df = df.drop(columns=DROP_COLUMNS)
    df = pd.get_dummies(df, columns=CATEGORICAL_COLUMNS, drop_first=True, dtype=int)

    return df


def main(args):
    df = prepare_data(get_data(args.input_data))

    print("Saving prepared data...")

    os.makedirs(args.output_data, exist_ok=True)
    df.to_csv(os.path.join(args.output_data, "prepared_data.csv"), index=False)
    print(f"Wrote {len(df)} rows to {args.output_data}")


if __name__ == "__main__":
    print("\n\n")
    print("*" * 60)

    args = parse_args()

    main(args)

    print("*" * 60)
    print("\n\n")
