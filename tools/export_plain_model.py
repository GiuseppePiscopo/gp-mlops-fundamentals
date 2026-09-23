"""Re-save an MLflow sklearn model's estimator as a plain joblib file, for custom scoring
deployments that don't use the MLflow no-code-deploy inferencing stack.

Usage:
    python tools/export_plain_model.py --model-dir model-mlflow/gp-mof-capstone-model/model --output model/model.pkl
"""

import argparse
import os
import pathlib

import joblib
import mlflow.sklearn


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", dest="model_dir", type=str, required=True)
    parser.add_argument("--output", dest="output", type=str, required=True)
    return parser.parse_args()


def main(args):
    # a plain Windows path with a drive letter (e.g. C:\...) gets misparsed as a URI scheme by mlflow
    model_uri = pathlib.Path(args.model_dir).resolve().as_uri()
    print("Loading MLflow model from", model_uri)
    model = mlflow.sklearn.load_model(model_uri)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    joblib.dump(model, args.output)
    print(f"Wrote plain joblib model to {args.output}")


if __name__ == "__main__":
    main(parse_args())
