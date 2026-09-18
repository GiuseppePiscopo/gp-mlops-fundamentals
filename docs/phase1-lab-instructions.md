# Lab project: MLOps Fundamentals training milestone - Phase 1 instructions

See the [README](../README.md) for overview and instructions on setting up the MLOps Fundamentals capstone project.

## Create a Compute cluster

Confirm the compute cluster doesn't already exist:

```cmd
az ml compute show --name gp-mof-capstone-compute
```

Create the Machine Learning compute cluster in the Azure CLI:

```cmd
az ml compute create --file .\config\gp-mof-capstone-compute.yml
```

## Create an Environment

Confirm the environment doesn't already exist:

```cmd
az ml environment show --name gp-mof-capstone-env
```

Create the Machine Learning environment in the Azure CLI:

```cmd
az ml environment create --file .\config\gp-mof-capstone-env.yml
```

## Run training script locally

Run the following command to execute a training script locally:

```cmd
cd ./src

python -m ridge.train --training_data ../data/sample/ --alpha 1.0

python -m ridge_scaled.train --training_data ../data/sample/ --alpha 1.0

python -m random_forest.train --training_data ../data/sample/ --n_estimators 100 --max_depth 10
```

Run these from inside the `src/` folder so the local project modules are resolved correctly.

## Create data asset in Azure Machine Learning

Confirm the data asset doesn't already exist:

```cmd
az ml data show --name gp-mof-capstone-data --version 1
```

Run the following command to create a data asset in Azure Machine Learning:

```cmd
az ml data create --file .\config\gp-mof-capstone-data.yml
```

## Run training job in Azure Machine Learning

Run the Ridge regression training job in Azure Machine Learning:

```cmd
az ml job create --file .\pipelines\gp-mof-capstone-job-ridge.yml
```

Run the scaled Ridge regression training job in Azure Machine Learning:

```cmd
az ml job create --file .\pipelines\gp-mof-capstone-job-ridge-scaled.yml
```

Run the Random Forest training job in Azure Machine Learning:

```cmd
az ml job create --file .\pipelines\gp-mof-capstone-job-rf.yml
```

## Check training job status

Run the following command to check the status of the most recently submitted job for the experiment:

```cmd
az ml job list -o table --experiment-name gp-mof-capstone
```

Alternatively, look for `name` in the output of the `az ml job create` command, e.g. `"name": "gifted_kiwi_x7y2z..."`. Then use it to check the job status:

```cmd
az ml job show --name <JOB_NAME>
```

## Run training job with different parameters in Azure Machine Learning

Run the Random Forest training job with different parameters in Azure Machine Learning, to obtain 3 different models in total.

Quicker training, less capacity usage:

```cmd
az ml job create --file .\pipelines\gp-mof-capstone-job-rf.yml --set inputs.n_estimators=50 --set inputs.max_depth=5
```

More trees, higher capacity usage:

```cmd
az ml job create --file .\pipelines\gp-mof-capstone-job-rf.yml --set inputs.n_estimators=300 --set inputs.max_depth=20
```

## Run an AutoML job in Azure Machine Learning

Confirm the MLTable data asset doesn't already exist:

```cmd
az ml data show --name gp-mof-capstone-data-mltable --version 1
```

Run the following command to register the MLTable data asset:

```cmd
az ml data create --file .\config\gp-mof-capstone-data-mltable.yml
```

Run the following command to launch the AutoML job:

```cmd
az ml job create --file .\pipelines\gp-mof-capstone-job-automl.yml
```

Compare the AutoML best run's metrics against the manual Ridge/Random Forest runs in Azure ML Studio.

## Inspect AutoML job results

Once completed, you can explore the details of the AutoML job and find the best run's metrics and artifacts.

If the AutoML job shows no data in the "Models + child jobs" tab (e.g. child runs failed after logging metrics), run this to get a trial comparison table from the job tags via CLI:

From a PowerShell console:

```powershell
.\tools\Get-AutoMLTrialSummary.ps1 -JobName <AUTOML_JOB_NAME>
```

From Windows Command Prompt:

```cmd
powershell -File .\tools\Get-AutoMLTrialSummary.ps1 -JobName <AUTOML_JOB_NAME>
```

## Compare manual and AutoML training runs

All jobs (manual, AutoML trials) log to the same `gp-mof-capstone` MLflow experiment. Run this any time, after any new job submission, to print all runs' params/metrics side by side in the console:

```cmd
python .\tools\compare_runs.py
```

## Register the best model for the Responsible AI dashboard

Find the model run with the best metrics (e.g. via `python .\tools\compare_runs.py`), then register its logged model as a named model asset:

```cmd
az ml model create --name gp-mof-capstone-model --version 1 --path azureml://jobs/<BEST_JOB_NAME>/outputs/artifacts/model --type mlflow_model
```

## Create data assets for Responsible AI dashboard in Azure ML

The dashboard needs separate train/test datasets, matching the same split/encoding the registered model was trained on.

Confirm the MLTable data assets don't already exist:

```cmd
az ml data show --name gp-mof-capstone-data-rai-train --version 2

az ml data show --name gp-mof-capstone-data-rai-test --version 2
```

Run the following command to generate them locally:

```cmd
python .\tools\prepare_rai_data.py
```

Register them as MLTable data assets:

```cmd
az ml data create --file .\config\gp-mof-capstone-data-rai-train.yml

az ml data create --file .\config\gp-mof-capstone-data-rai-test.yml
```

## Run the job for the Responsible AI dashboard

Run the Responsible AI pipeline against the registered model:

```cmd
az ml job create --file .\pipelines\gp-mof-capstone-job-rai.yml
```

Once completed, open the registered model (`gp-mof-capstone-model`) in Azure ML Studio and go to its "Responsible AI" tab to explore the dashboard.

## Promote best model to staging environment

Promote the registered best model to the staging environment:

```cmd
az ml model update --name gp-mof-capstone-model --version 1 --set properties.stage=staging
```

## Run sweep job to tune hyperparameters in Azure ML

Run the following command to start the hyperparameter sweep job:

```cmd
az ml job create --file .\pipelines\gp-mof-capstone-job-rf-sweep.yml
```

## Run pipeline steps locally

Run the preprocessing step:

```cmd
python .\src\pipeline_rf\prepare_data.py --input_data .\data\sample --output_data .\data\pipeline-rf-prepared
```

Run the training step on the prepared output:

```cmd
python .\src\pipeline_rf\train.py --training_data .\data\pipeline-rf-prepared --model_output .\data\pipeline-rf-model --n_estimators 300 --max_depth 20
```

The first step prepares the tabular data; the second trains, evaluates, and saves the MLflow model.

## Run pipeline job in Azure Machine Learning

Run the following command to submit the two-step Random Forest pipeline job to Azure Machine Learning:

```cmd
az ml job create --file .\pipelines\gp-mof-capstone-pipeline.yml
```
