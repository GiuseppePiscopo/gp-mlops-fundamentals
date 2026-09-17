"""Compare metrics across all runs (manual + AutoML trials) in the shared MLflow experiment.

Re-run this any time after launching new jobs (manual or AutoML): it always reflects
the current state of the experiment, no manual bookkeeping needed.

Usage:
    python tools/compare_runs.py [--experiment_name gp-mof-capstone]
"""

import argparse
import subprocess

import mlflow


def get_tracking_uri():
    result = subprocess.run(
        "az ml workspace show --query mlflow_tracking_uri -o tsv",
        capture_output=True,
        text=True,
        shell=True,
        check=True,
    )
    return result.stdout.strip()


def get_algorithm_column(runs):
    """Resolve the algorithm/model per run.

    Manual scripts: inferred from the display name.
    AutoML trials: not logged per-run, only on the parent job's semicolon-separated
    tags. Joined back by matching the primary metric value (unique per trial).
    """
    algorithm = runs["tags.mlflow.runName"].map(
        lambda name: "Ridge" if "ridge" in str(name) else ("RandomForest" if "random-forest" in str(name) else None)
    )

    parent_rows = runs[runs["tags.run_algorithm_000"].notna()]
    if not parent_rows.empty and "metrics.normalized_root_mean_squared_error" in runs.columns:
        parent = parent_rows.iloc[0]
        scores = [round(float(s), 8) for s in parent["tags.score_000"].split(";")]
        algos = parent["tags.run_algorithm_000"].split(";")
        score_to_algo = dict(zip(scores, algos))

        automl_scores = runs["metrics.normalized_root_mean_squared_error"].round(8)
        algorithm = algorithm.combine_first(automl_scores.map(score_to_algo))

    return algorithm


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment_name", default="gp-mof-capstone")
    args = parser.parse_args()

    mlflow.set_tracking_uri(get_tracking_uri())
    runs = mlflow.search_runs(experiment_names=[args.experiment_name])

    if runs.empty:
        print(f"No runs found for experiment '{args.experiment_name}'.")
        return

    # only columns that exist: manual and AutoML runs log different params/metrics
    param_cols = [c for c in runs.columns if c.startswith("params.")]
    metric_cols = [c for c in runs.columns if c.startswith("metrics.")]
    columns = ["tags.mlflow.runName", "status", *param_cols, *metric_cols]
    columns = [c for c in columns if c in runs.columns]

    table = runs[columns].rename(columns=lambda c: c.replace("metrics.", "").replace("params.", ""))
    table = table.rename(columns={"tags.mlflow.runName": "run"})

    # manual scripts and AutoML log the same metrics under different names; merge them into one column each

    # manual MAPE is a fraction, AutoML's is already in percentage points
    table["MAPE"] = table["MAPE"] * 100
    metric_aliases = {
        "MAE": "mean_absolute_error",
        "RMSE": "root_mean_squared_error",
        "R2": "r2_score",
        "MAPE": "mean_absolute_percentage_error",
    }
    for canonical, automl_name in metric_aliases.items():
        table[canonical] = table[canonical].combine_first(table[automl_name])

    table["Algorithm"] = get_algorithm_column(runs)

    # keep only the params and the canonical, merged metrics - drop AutoML-only extras (spearman_correlation, ...)
    keep_cols = ["run", "status", "Algorithm", *[c.replace("params.", "") for c in param_cols], *metric_aliases.keys()]
    table = table[[c for c in keep_cols if c in table.columns]]
    table = table.dropna(subset=list(metric_aliases.keys()), how="all")

    print(table.sort_values("status").to_string(index=False))


if __name__ == "__main__":
    main()
