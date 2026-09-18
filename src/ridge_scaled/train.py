import argparse

import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from common.training_utils import RANDOM_SEED, eval_model, get_data

TARGET_COLUMN = "Rented Bike Count"
CATEGORICAL_COLUMNS = ["Seasons", "Holiday", "Functioning Day"]
DROP_COLUMNS = ["Date"]


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


def prepare_data(df):
    print("Preparing data...")

    df = df.drop(columns=DROP_COLUMNS)
    df = pd.get_dummies(df, columns=CATEGORICAL_COLUMNS, drop_first=True)

    X = df.drop(columns=[TARGET_COLUMN]).values
    y = df[TARGET_COLUMN].values

    # fixed seed: same split as the baseline Ridge and Random Forest scripts
    return train_test_split(X, y, test_size=0.20, random_state=RANDOM_SEED)


def train_model(alpha, X_train, y_train):
    mlflow.log_param("alpha", alpha)
    mlflow.log_param("scaling", "standard")

    print("Training model...")

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=alpha, random_state=RANDOM_SEED)),
        ]
    )
    return model.fit(X_train, y_train)


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
