# Lab project: MLOps Fundamentals training milestone - Phase 2 instructions

See the [README](../README.md) for overview and instructions on setting up the MLOps Fundamentals capstone project.

## Part 1: Deploy to managed endpoint

### Promote the model to Production

Promote the registered best model to the production environment:

```cmd
az ml model update --name gp-mof-capstone-model --version 1 --set tags.stage=production
```

### Create the managed online endpoint

Create the managed online endpoint in Azure Machine Learning:

```cmd
az ml online-endpoint create --file .\config\gp-mof-capstone-endpoint.yml
```

### Grant the endpoint identity access to workspace assets

The managed endpoint has a system-assigned identity. Grant it the `AzureML Data Scientist` role on the workspace before creating a deployment, so it can read the registered model environment:

```powershell
$endpointPrincipalId = az ml online-endpoint show --name gp-mof-capstone-endpoint --query identity.principal_id -o tsv

$workspaceScope = "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/gp-mof-rg-dev/providers/Microsoft.MachineLearningServices/workspaces/gp-mof-ws-dev"

az role assignment create --assignee-object-id $endpointPrincipalId --assignee-principal-type ServicePrincipal --role "AzureML Data Scientist" --scope $workspaceScope
```

Verify that the role assignment is visible at the workspace scope:

```powershell
az role assignment list --assignee-object-id $endpointPrincipalId --scope $workspaceScope --query "[].roleDefinitionName" -o tsv
```

Wait a few minutes for the role assignment to propagate before creating the deployment.

### Create the blue deployment from the registered MLflow model

Create the deployment from the registered MLflow model:

```cmd
az ml online-deployment create --file .\config\gp-mof-capstone-deployment-blue.yml
```

### Route 100% of traffic to the blue deployment

Route all endpoint traffic to the blue deployment:

```cmd
az ml online-endpoint update --name gp-mof-capstone-endpoint --traffic "blue=100"
```

### Verify the endpoint

Check the endpoint details:

```cmd
az ml online-endpoint show --name gp-mof-capstone-endpoint
```

Confirm that the endpoint provisioning state is `Succeeded` and that the traffic mapping shows `blue: 100`.

### Test with a REST call

The registered model (`random_forest/train.py`, no MLflow signature) expects `input_data` to be a numeric matrix containing the raw values as they come out of `prepare_data` in `common/training_utils.py`: `Date` column dropped, categorical columns `Seasons`/`Holiday`/`Functioning Day` one-hot encoded (`drop_first=True`), no target column. The payload is in [data/test-request/request.json](../data/test-request/request.json) (sample row taken from `data/rai-train/data.csv`, same encoding as training).

Invoke the endpoint with the test payload:

```cmd
az ml online-endpoint invoke --name gp-mof-capstone-endpoint --request-file data\test-request\request.json
```

### Check the response

Check the returned value in the terminal (the `Rented Bike Count` prediction) and the request logs in Azure ML Studio (deployment "Log" tab).

### Recreate a failed endpoint or deployment

To restart with a new endpoint identity, delete the endpoint and all of its deployments:

```cmd
az ml online-endpoint delete --name gp-mof-capstone-endpoint --yes
```

Then repeat the endpoint creation, role assignment, and blue deployment steps in that order.

If the endpoint succeeded but a deployment (blue or green) failed, delete and recreate only that deployment:

```cmd
az ml online-deployment delete --name blue --endpoint-name gp-mof-capstone-endpoint --yes
az ml online-deployment delete --name green --endpoint-name gp-mof-capstone-endpoint --yes
```

This same permission-propagation issue can resurface for any new deployment on this endpoint (including green in Part 2), even though the endpoint itself hasn't changed. When a deployment reports `workspaces/environments/read`, delete the workspace-level `AzureML Data Scientist` assignment for the current endpoint principal ID:

```powershell
az role assignment delete --assignee-object-id $endpointPrincipalId --role "AzureML Data Scientist" --scope $workspaceScope
```

Assign the role again, wait a few minutes for propagation, and retry the deployment.

## Part 2: Deploy with a custom scoring script

### Export the trained model as a plain artifact

Download the registered MLflow model's files, then re-save the underlying estimator as a plain joblib file (no MLflow flavor). Run the export in a dedicated virtual environment pinned to the same versions as the scoring environment (`config/gp-mof-capstone-env-score-conda.yml`). Create it with the `py` launcher targeting a specific Python 3.9–3.12 interpreter (numpy 1.26.4 has no prebuilt wheel for newer versions, and plain `python` may resolve to one on your machine):

```cmd
az ml model download --name gp-mof-capstone-model --version 3 --download-path .\model-mlflow

py -3.11 -m venv .venv-export

.venv-export\Scripts\python.exe -m pip install -r .\tools\export-requirements.txt

.venv-export\Scripts\python.exe .\tools\export_plain_model.py --model-dir model-mlflow\gp-mof-capstone-model\model --output model\model.pkl
```

If you already created `.venv-export` with the wrong Python version, delete the folder first (`Remove-Item -Recurse -Force .venv-export`) before recreating it — reusing it with a different interpreter leaves a broken mix of compiled extensions.

### Register the plain artifact as a custom model

Register it as a separate model, with its own version lineage independent from the MLflow model, and type `custom_model`:

```cmd
az ml model create --name gp-mof-capstone-model-custom --version 1 --path .\model\model.pkl --type custom_model
```

### Promote the custom model to Production

Tag this custom model version as production too:

```cmd
az ml model update --name gp-mof-capstone-model-custom --version 1 --set tags.stage=production
```

### Define the custom scoring environment

Create the scoring environment:

```cmd
az ml environment create --file .\config\gp-mof-capstone-env-score.yml
```

### Create the green deployment

Create the deployment:

```cmd
az ml online-deployment create --file .\config\gp-mof-capstone-deployment-green.yml
```

New deployments start at 0% traffic, so no traffic update is needed. Confirm it:

```cmd
az ml online-endpoint show --name gp-mof-capstone-endpoint --query traffic
```

### Test the green deployment directly

Blue and green have different input schemas (blue: pre-processed features; green: raw data), so always target a specific deployment instead of relying on the endpoint's traffic split — a real blue/green rollout would instead require an identical input contract between deployments.

Invoke blue with the existing payload, and green with a raw payload:

```cmd
az ml online-endpoint invoke --name gp-mof-capstone-endpoint --deployment-name blue --request-file data\test-request\request.json

az ml online-endpoint invoke --name gp-mof-capstone-endpoint --deployment-name green --request-file data\test-request\request-raw.json
```

### Check the response

Compare the `Rented Bike Count` prediction returned by green against the one returned by blue, and check each deployment's request logs in Azure ML Studio (deployment "Log" tab).
