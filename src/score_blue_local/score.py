import glob
import json
import os

import mlflow


def _find_mlmodel_dir(root):
    for mlmodel_path in glob.glob(os.path.join(root, "**", "MLmodel"), recursive=True):
        return os.path.dirname(mlmodel_path)
    raise FileNotFoundError(f"No MLmodel file found under {root}")


def init():
    global model

    print("\n\n")
    print("*" * 60)

    model_dir = _find_mlmodel_dir(os.getenv("AZUREML_MODEL_DIR"))
    print("Loading MLflow model from", model_dir)
    model = mlflow.sklearn.load_model(model_dir)

    print("Init complete")
    print("*" * 60)
    print("\n\n")


def run(raw_data):
    print("Request received")

    # same contract as the remote no-code MLflow deployment: pre-processed numeric matrix
    records = json.loads(raw_data)["input_data"]
    predictions = model.predict(records)

    print("Request processed")

    return predictions.tolist()
