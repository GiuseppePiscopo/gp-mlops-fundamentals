import json
import os

import joblib
import pandas as pd

try:
    # available in the scoring environment via azureml-ai-monitoring; dummy fallback
    # lets the module stay importable on machines without the Azure ML SDK
    from azureml.ai.monitoring import Collector

    inputs_collector = Collector(name="model_inputs")
    outputs_collector = Collector(name="model_outputs")
except Exception:  # pragma: no cover
    class _NoOpCollector:
        def collect(self, *args, **kwargs):
            return None

    inputs_collector = _NoOpCollector()
    outputs_collector = _NoOpCollector()

DROP_COLUMNS = ["Date"]
CATEGORICAL_COLUMNS = ["Seasons", "Holiday", "Functioning Day"]
# fixed at training time (drop_first=True): a batch missing a category would otherwise
# produce fewer dummy columns and shift the model's input vector
EXPECTED_COLUMNS = [
    "Hour",
    "Temperature(°C)",
    "Humidity(%)",
    "Wind speed (m/s)",
    "Visibility (10m)",
    "Dew point temperature(°C)",
    "Solar Radiation (MJ/m2)",
    "Rainfall(mm)",
    "Snowfall (cm)",
    "Seasons_Spring",
    "Seasons_Summer",
    "Seasons_Winter",
    "Holiday_No Holiday",
    "Functioning Day_Yes",
]


def init():
    global model

    print("\n\n")
    print("*" * 60)

    model_path = os.path.join(os.getenv("AZUREML_MODEL_DIR"), "model.pkl")
    print("Loading model from", model_path)
    model = joblib.load(model_path)

    print("Init complete")
    print("*" * 60)
    print("\n\n")


def prepare_data(records):
    df = pd.DataFrame(records)
    df = df.drop(columns=DROP_COLUMNS)

    # explicit per-category checks instead of pd.get_dummies: get_dummies only creates
    # columns for categories present in the batch, so a single-row request (exactly one
    # value per categorical column) would have drop_first remove its only category,
    # silently zeroing every dummy column for that field after the reindex below
    df["Seasons_Spring"] = (df["Seasons"] == "Spring").astype(int)
    df["Seasons_Summer"] = (df["Seasons"] == "Summer").astype(int)
    df["Seasons_Winter"] = (df["Seasons"] == "Winter").astype(int)
    df["Holiday_No Holiday"] = (df["Holiday"] == "No Holiday").astype(int)
    df["Functioning Day_Yes"] = (df["Functioning Day"] == "Yes").astype(int)
    df = df.drop(columns=CATEGORICAL_COLUMNS)

    df = df.reindex(columns=EXPECTED_COLUMNS, fill_value=0)

    return df


def run(raw_data):
    print("Request received")

    records = json.loads(raw_data)["data"]
    df = prepare_data(records)
    predictions = model.predict(df.values)

    # production inference data for Azure ML model monitoring (data_collector must be
    # enabled on the deployment; blue uses auto-instrumentation, green logs explicitly here)
    try:
        context = inputs_collector.collect(df)
        outputs_collector.collect(pd.DataFrame(predictions, columns=["prediction"]), context)
    except Exception as ex:  # data collection must never break scoring
        print(f"Data collection skipped: {ex}")

    print("Request processed")

    return predictions.tolist()
