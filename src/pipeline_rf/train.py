import argparse
import glob
import os
import shutil

import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split

RANDOM_SEED = 42
TARGET_COLUMN = "Rented Bike Count"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--training_data", dest="training_data", type=str)
    parser.add_argument("--model_output", dest="model_output", type=str)
    parser.add_argument("--n_estimators", dest="n_estimators", type=int, default=300)
    parser.add_argument("--max_depth", dest="max_depth", type=int, default=20)
    return parser.parse_args()


def load_data(path):
    print("Reading prepared data...")

    csv_files = glob.glob(os.path.join(path, "*.csv"))
    if not csv_files:
        raise RuntimeError(f"No prepared CSV files found in provided data path: {path}")
    return pd.read_csv(csv_files[0])


def train_model(n_estimators, max_depth, X_train, y_train):
    mlflow.log_param("n_estimators", n_estimators)
    mlflow.log_param("max_depth", max_depth)
    print("Training model...")

    return RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    ).fit(X_train, y_train)


def evaluate_model(model, X_test, y_test):
    print("Evaluating model...")

    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    rmse = mean_squared_error(y_test, predictions) ** 0.5
    r2 = r2_score(y_test, predictions)
    nonzero_mask = y_test != 0
    mape = mean_absolute_percentage_error(y_test[nonzero_mask], predictions[nonzero_mask])

    for name, value in {"MAE": mae, "RMSE": rmse, "R2": r2, "MAPE": mape}.items():
        mlflow.log_metric(name, value)
        print(f"{name}: {value}")


def main(args):
    df = load_data(args.training_data)
    X = df.drop(columns=[TARGET_COLUMN]).values
    y = df[TARGET_COLUMN].values
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=RANDOM_SEED)

    with mlflow.start_run():
        model = train_model(args.n_estimators, args.max_depth, X_train, y_train)
        evaluate_model(model, X_test, y_test)
        print("Saving model...")
        if os.path.exists(args.model_output):
            shutil.rmtree(args.model_output)
        os.makedirs(args.model_output)
        mlflow.sklearn.save_model(model, args.model_output)


if __name__ == "__main__":
    print("\n\n")
    print("*" * 60)

    args = parse_args()

    main(args)

    print("*" * 60)
    print("\n\n")
