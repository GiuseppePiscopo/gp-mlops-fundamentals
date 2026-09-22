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
