import argparse
import glob
import os

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split

TARGET_COLUMN = "Rented Bike Count"
CATEGORICAL_COLUMNS = ["Seasons", "Holiday", "Functioning Day"]
# Date is dropped: Hour/Seasons already capture the seasonality signal for this baseline
DROP_COLUMNS = ["Date"]
# fixed across scripts so runs stay comparable in MLflow
RANDOM_SEED = 42


def parse_args():
    # setup arg parser
    parser = argparse.ArgumentParser()

    # add arguments
    parser.add_argument("--training_data", dest="training_data", type=str)
    parser.add_argument("--alpha", dest="alpha", type=float, default=1.0)

    # parse args
    args = parser.parse_args()

    # return args
    return args


def main(args):
    with mlflow.start_run():
        # read data
        df = get_data(args.training_data)

        # prepare data
        X_train, X_test, y_train, y_test = prepare_data(df)

        # train model
        model = train_model(args.alpha, X_train, y_train)

        # evaluate model
        eval_model(model, X_test, y_test)

        mlflow.sklearn.log_model(model, artifact_path="model")


def get_data(path):
    print("Reading data...")

    if os.path.isdir(path):
        csv_files = glob.glob(os.path.join(path, "*.csv"))
        if not csv_files:
            raise RuntimeError(f"No CSV files found in provided data path: {path}")
        df = pd.concat((pd.read_csv(f) for f in csv_files), ignore_index=True)
    else:
        df = pd.read_csv(path)

    return df


def prepare_data(df):
    print("Preparing data...")

    df = df.drop(columns=DROP_COLUMNS)
    df = pd.get_dummies(df, columns=CATEGORICAL_COLUMNS, drop_first=True)

    X = df.drop(columns=[TARGET_COLUMN]).values
    y = df[TARGET_COLUMN].values

    # fixed seed: reproducible split, comparable across scripts/runs
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=RANDOM_SEED)

    return X_train, X_test, y_train, y_test


def train_model(alpha, X_train, y_train):
    mlflow.log_param("alpha", alpha)

    print("Training model...")

    model = Ridge(alpha=alpha, random_state=RANDOM_SEED).fit(X_train, y_train)

    return model


def eval_model(model, X_test, y_test):
    y_hat = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_hat)
    rmse = np.sqrt(mean_squared_error(y_test, y_hat))
    r2 = r2_score(y_test, y_hat)
    # zero targets make MAPE explode (sklearn clips the denominator to an epsilon), so exclude them
    nonzero_mask = y_test != 0
    mape = mean_absolute_percentage_error(y_test[nonzero_mask], y_hat[nonzero_mask])

    print("MAE:", mae)
    print("RMSE:", rmse)
    print("R2:", r2)
    print("MAPE:", mape)

    mlflow.log_metric("MAE", mae)
    mlflow.log_metric("RMSE", rmse)
    mlflow.log_metric("R2", r2)
    mlflow.log_metric("MAPE", mape)


# run script
if __name__ == "__main__":
    # add space in logs
    print("\n\n")
    print("*" * 60)

    # parse args
    args = parse_args()

    # run main function
    main(args)

    # add space in logs
    print("*" * 60)
    print("\n\n")
