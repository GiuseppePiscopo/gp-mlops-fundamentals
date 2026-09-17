import glob
import os

import mlflow
import numpy as np
import pandas as pd
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
