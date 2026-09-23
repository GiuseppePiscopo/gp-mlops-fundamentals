# Lab project: MLOps Fundamentals training milestone - Phase 2 instructions

See the [README](../README.md) for overview and instructions on setting up the MLOps Fundamentals capstone project.

## Part 1

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
az ml online-deployment create --file .\config\gp-mof-capstone-deployment.yml
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

If the endpoint succeeded but only the blue deployment failed, delete and recreate only the deployment:

```cmd
az ml online-deployment delete --name blue --endpoint-name gp-mof-capstone-endpoint --yes
```

When the new deployment reports `workspaces/environments/read`, delete the workspace-level `AzureML Data Scientist` assignment for the current endpoint principal ID:

```powershell
az role assignment delete --assignee-object-id $endpointPrincipalId --role "AzureML Data Scientist" --scope $workspaceScope
```

Assign the role again, wait a few minutes for propagation, and retry the deployment.
