import argparse

import mlflow
import mlflow.sklearn
from sklearn.linear_model import Ridge

from common.training_utils import RANDOM_SEED, eval_model, get_data, prepare_data


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


def train_model(alpha, X_train, y_train):
    mlflow.log_param("alpha", alpha)

    print("Training model...")

    model = Ridge(alpha=alpha, random_state=RANDOM_SEED).fit(X_train, y_train)

    return model


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
