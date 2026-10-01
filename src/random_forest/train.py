import argparse

import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestRegressor

from common.training_utils import RANDOM_SEED, eval_model, get_data, prepare_data


def parse_args():
    # setup arg parser
    parser = argparse.ArgumentParser()

    # add arguments
    parser.add_argument("--training_data", dest="training_data", type=str)
    parser.add_argument("--n_estimators", dest="n_estimators", type=int, default=100)
    parser.add_argument("--max_depth", dest="max_depth", type=int, default=None)
    parser.add_argument(
        "--fail_for_alert_test",
        type=lambda x: x.lower() == "true",
        default=False,
    )

    # parse args
    args = parser.parse_args()

    # return args
    return args


def main(args):

    if args.fail_for_alert_test:
        raise RuntimeError("ALERT TEST: intentional Azure ML training job failure")

    with mlflow.start_run():
        # read data
        df = get_data(args.training_data)

        # prepare data
        X_train, X_test, y_train, y_test = prepare_data(df)

        # train model
        model = train_model(args.n_estimators, args.max_depth, X_train, y_train)

        # evaluate model
        eval_model(model, X_test, y_test)

        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            # Required by Azure ML's generated MLflow scoring script.
            extra_pip_requirements=["azureml-ai-monitoring"],
        )


def train_model(n_estimators, max_depth, X_train, y_train):
    mlflow.log_param("n_estimators", n_estimators)
    mlflow.log_param("max_depth", max_depth)

    print("Training model...")

    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    ).fit(X_train, y_train)

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
