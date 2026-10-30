# Lab project: MLOps Fundamentals training milestone - Phase 3 instructions

See the [README](../README.md) for overview and instructions on setting up the MLOps Fundamentals capstone project.

Goal: merge to `main` (via PR, with branch protection) → Azure ML training job → automatic evaluation gate → manual approval → automatic deployment.

The workflow is [ml-pipeline.yml](../.github/workflows/ml-pipeline.yml). It has two jobs: `train-and-evaluate` (training job, evaluation gate, model registered with `stage=staging`) and `deploy` (waits for approval on the `production` environment, updates the `blue` deployment, promotes the model to `stage=production`).

The training job is `pipelines/gp-mof-capstone-job-rf.yml`. The gate in `tools/evaluate.py` requires `R2 >= 0.80` and `RMSE <= 300` (the Random Forest baseline scores about `0.85` and `250`).

## Part 1: Prepare the evaluation gate

### Run the evaluation gate locally

Run the gate against a completed Random Forest job (find a `<JOB_NAME>` with `az ml job list -o table`). It passes with the default thresholds:

```cmd
python .\tools\evaluate.py --job_name <JOB_NAME>
```

Make it fail with a stricter threshold, and check that the exit code is not zero:

```cmd
python .\tools\evaluate.py --job_name <JOB_NAME> --min_r2 0.9
```

### Recreate the managed online endpoint

The deployment job updates the existing `blue` deployment, so the endpoint must exist. An endpoint without deployments isn't billed, so create it now: the role assignment propagates while you set up GitHub in the next parts. Confirm that it doesn't exist:

```cmd
az ml online-endpoint show --name gp-mof-capstone-endpoint
```

Create the endpoint and grant its identity access to the workspace:

```cmd
az ml online-endpoint create --file .\config\gp-mof-capstone-endpoint.yml
```

```powershell
$endpointPrincipalId = az ml online-endpoint show --name gp-mof-capstone-endpoint --query identity.principal_id -o tsv

$workspaceScope = "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/gp-mof-rg-dev/providers/Microsoft.MachineLearningServices/workspaces/gp-mof-ws-dev"

az role assignment create --assignee-object-id $endpointPrincipalId --assignee-principal-type ServicePrincipal --role "AzureML Data Scientist" --scope $workspaceScope
```

## Part 2: Create the GitHub repository

Log in to GitHub through the browser, with the scopes needed to create the repository, push workflows and manage secrets, environments and branch protection. A fine-grained personal access token can't create repositories in a personal account:

```powershell
gh auth login --hostname github.com --git-protocol https --web --scopes "repo,workflow"

gh auth status
```

Answer `Y` to "Authenticate Git with your GitHub credentials?" so `git push github` works over HTTPS (it only affects `github.com`, not the Bitbucket remote). Copy the one-time code and confirm in the browser.

Create the public GitHub repository without pushing anything yet, and add it as the `github` remote. The Bitbucket `origin` remote stays as it is:

```powershell
gh repo create gp-mlops-fundamentals --public --description "MLOps Fundamentals capstone project"

git remote add github https://github.com/GiuseppePiscopo/gp-mlops-fundamentals.git

git remote -v
```

From now on, every `gh` command targets the repository explicitly with `--repo GiuseppePiscopo/gp-mlops-fundamentals`, because `origin` isn't a GitHub remote.

## Part 3: Set up OIDC authentication

### Create the app registration and service principal

Create the Microsoft Entra ID app registration and its service principal, and assign `Contributor` on the resource group:

```powershell
$appId = az ad app create --display-name "gp-mof-capstone-app-ghactions" --query appId -o tsv

az ad sp create --id $appId

$subscriptionId = az account show --query id -o tsv

az role assignment create --assignee $appId --role contributor --scope "/subscriptions/$subscriptionId/resourceGroups/gp-mof-rg-dev"
```

### Create the federated credentials

Extract the subject prefix of the repository:

```powershell
$subjectPrefix = gh api repos/GiuseppePiscopo/gp-mlops-fundamentals/actions/oidc/customization/sub --jq .sub_claim_prefix
```

Generate the credential files from the templates (the `*.local.json` outputs are git-ignored):

```powershell
foreach ($name in "production", "main", "pr") {
  (Get-Content ".\config\gp-mof-capstone-fic-$name.template.json") -replace '<SUBJECT_PREFIX>', $subjectPrefix | Set-Content -Encoding ascii ".\config\gp-mof-capstone-fic-$name.local.json"
}
```

Create the federated credential for the `deploy` job, which runs in the `production` environment:

```powershell
az ad app federated-credential create --id $appId --parameters "@.\config\gp-mof-capstone-fic-production.local.json"
```

Create the federated credential for the `train-and-evaluate` job, which runs on the `main` branch:

```powershell
az ad app federated-credential create --id $appId --parameters "@.\config\gp-mof-capstone-fic-main.local.json"
```

Create the federated credential for the `train-and-evaluate` job, which runs on pull requests:

```powershell
az ad app federated-credential create --id $appId --parameters "@.\config\gp-mof-capstone-fic-pr.local.json"
```

Verify them:

```powershell
az ad app federated-credential list --id $appId --query "[].{name:name, subject:subject}" -o table
```

### Create the GitHub secrets

Create the identifiers used by `azure/login@v2` (not sensitive: OIDC needs no credentials) and the workspace and resource group names used by the workflow. Run this in the same terminal as the commands above, so `$appId` and `$subscriptionId` are set:

```powershell
$repo = "GiuseppePiscopo/gp-mlops-fundamentals"

gh secret set AZURE_CLIENT_ID --repo $repo --body $appId

gh secret set AZURE_TENANT_ID --repo $repo --body (az account show --query tenantId -o tsv)

gh secret set AZURE_SUBSCRIPTION_ID --repo $repo --body $subscriptionId

gh secret set GP_MOF_AZURE_WORKSPACE_DEV --repo $repo --body gp-mof-ws-dev

gh secret set GP_MOF_AZURE_RESOURCE_GROUP_DEV --repo $repo --body gp-mof-rg-dev

gh secret list --repo $repo
```

## Part 4: Create the production environment

Create the `production` environment with the current GitHub user as required reviewer (self-review is allowed, as you are the only maintainer):

```powershell
$userId = [long](gh api user --jq .id)

@{ reviewers = @(@{ type = "User"; id = $userId }) } | ConvertTo-Json -Depth 4 -Compress | gh api --method PUT repos/GiuseppePiscopo/gp-mlops-fundamentals/environments/production --input -
```

Verify the protection rule:

```powershell
gh api repos/GiuseppePiscopo/gp-mlops-fundamentals/environments/production --jq ".protection_rules"
```

## Part 5: First pipeline run

### Create the blue deployment

The `deploy` job updates the existing `blue` deployment, so create it before starting the workflow. Confirm the endpoint exists and has no deployments yet:

```cmd
az ml online-deployment list --endpoint-name gp-mof-capstone-endpoint -o table
```

Create the blue deployment and route all traffic to it:

```cmd
az ml online-deployment create --file .\config\gp-mof-capstone-deployment-blue.yml

az ml online-endpoint update --name gp-mof-capstone-endpoint --traffic "blue=100"
```

Confirm that the deployment provisioning state is `Succeeded`:

```cmd
az ml online-deployment show --name blue --endpoint-name gp-mof-capstone-endpoint --query provisioning_state -o tsv
```

Verify the endpoint:

```cmd
az ml online-endpoint invoke --name gp-mof-capstone-endpoint --deployment-name blue --request-file data\test-request\request.json
```

### Push `main` to GitHub

Commit the Phase 3 files if they aren't committed yet, then push the repository. This first push goes straight to `main` because branch protection isn't enabled yet, and it starts the workflow:

```powershell
git status --short

git push github main
```

Check that a run started for the pushed commit:

```powershell
gh run list --repo GiuseppePiscopo/gp-mlops-fundamentals --workflow ml-pipeline.yml --limit 3
```

If no run starts, trigger it manually:

```powershell
gh workflow run ml-pipeline.yml --repo GiuseppePiscopo/gp-mlops-fundamentals --ref main
```

### Follow the run

In a dedicated terminal, watch the run until the `deploy` job waits for approval, after the training job and the gate have passed:

```powershell
$runId = gh run list --repo GiuseppePiscopo/gp-mlops-fundamentals --workflow ml-pipeline.yml --limit 1 --json databaseId --jq ".[0].databaseId"

gh run watch $runId --repo GiuseppePiscopo/gp-mlops-fundamentals
```

### Approve the deployment

Approve the deployment (alternatively, open the run in GitHub and use "Review deployments"):

```powershell
$runId = gh run list --repo GiuseppePiscopo/gp-mlops-fundamentals --workflow ml-pipeline.yml --limit 1 --json databaseId --jq ".[0].databaseId"

$envId = [long](gh api repos/GiuseppePiscopo/gp-mlops-fundamentals/environments/production --jq .id)

@{ environment_ids = @($envId); state = "approved"; comment = "Approved" } | ConvertTo-Json -Compress | gh api --method POST repos/GiuseppePiscopo/gp-mlops-fundamentals/actions/runs/$runId/pending_deployments --input -
```

The watch in the dedicated terminal ends when the run completes.

### Verify the deployment

Check which model version the blue deployment serves, and the model stages in the registry:

```cmd
az ml online-deployment show --name blue --endpoint-name gp-mof-capstone-endpoint --query model -o tsv

az ml model list --name gp-mof-capstone-model --query "[].{version:version, stage:tags.stage, job:tags.job}" -o table
```

The deployed version has `stage=production`; the previous production versions are `archived`.

## Part 6: Protect `main` and work with PRs

### Protect the main branch

Require a PR with one approving review, and the `train-and-evaluate` check passing on a branch that is up to date with `main`, before merging into `main`. Administrators aren't enforced, so as the only maintainer you can still merge your own PRs with `--admin`:

```powershell
@{
  required_status_checks = @{ strict = $true; contexts = @("train-and-evaluate") }
  enforce_admins = $false
  required_pull_request_reviews = @{ required_approving_review_count = 1 }
  restrictions = $null
} | ConvertTo-Json -Depth 4 | gh api --method PUT repos/GiuseppePiscopo/gp-mlops-fundamentals/branches/main/protection --input -
```

Verify the protection:

```powershell
gh api repos/GiuseppePiscopo/gp-mlops-fundamentals/branches/main/protection --jq "{required_pull_request_reviews, required_status_checks}"
```

A PR that changes nothing under `src/` or `pipelines/` doesn't run the workflow, so the check is never reported: merge it with `--admin`. If `main` moves after the check passed, update the PR branch (this restarts the check):

```powershell
gh pr update-branch <BRANCH> --repo GiuseppePiscopo/gp-mlops-fundamentals
```

### Verify that the workflow runs on the PR and on merge

Work on a feature branch created from `github/main` and open a PR for any change under `src/` (here, only a comment):

```powershell
git fetch github

git switch -c feature/trigger-check-1 --no-track github/main

Add-Content .\src\random_forest\train.py "`n# trigger check nr 1"

git commit -am "chore(repo): verifica il trigger del workflow nr 1"

git push github feature/trigger-check-1

gh pr create --repo GiuseppePiscopo/gp-mlops-fundamentals --base main --head feature/trigger-check-1 --title "Verify workflow trigger nr 1" --body "Trigger check"
```

Confirm that opening the PR starts a run with the `pull_request` event, which trains and evaluates only (`deploy` is skipped). In a dedicated terminal, watch it:

```powershell
$runId = gh run list --repo GiuseppePiscopo/gp-mlops-fundamentals --workflow ml-pipeline.yml --branch feature/trigger-check-1 --limit 1 --json databaseId --jq ".[0].databaseId"

gh run watch $runId --repo GiuseppePiscopo/gp-mlops-fundamentals
```

Check that the PR check passed:

```powershell
gh pr checks feature/trigger-check-1 --repo GiuseppePiscopo/gp-mlops-fundamentals
```

Merge the PR and confirm that a new run starts with the `push` event:

```powershell
gh pr merge feature/trigger-check-1 --repo GiuseppePiscopo/gp-mlops-fundamentals --squash --admin --delete-branch

gh run list --repo GiuseppePiscopo/gp-mlops-fundamentals --workflow ml-pipeline.yml --limit 3
```

Approve this run as in Part 5, then sync the local `main` and delete the branch (`-D` because the squash merge rewrites the commits):

```powershell
git switch main

git pull github main

git branch -D feature/trigger-check-1
```

## Part 7: End-to-end test

### Degrade the model

Reduce the Random Forest capacity so the model misses the gate (`n_estimators=50`, `max_depth=5` gives `R2` of about `0.73`), and open a PR:

```powershell
git fetch github

git switch -c experiment/tune-model-1 --no-track github/main

(Get-Content .\pipelines\gp-mof-capstone-job-rf.yml) -replace 'n_estimators: 100', 'n_estimators: 50' -replace 'max_depth: 10', 'max_depth: 5' | Set-Content .\pipelines\gp-mof-capstone-job-rf.yml

git commit -am "test(repo): degrada intenzionalmente il modello"

git push github experiment/tune-model-1

gh pr create --repo GiuseppePiscopo/gp-mlops-fundamentals --base main --head experiment/tune-model-1 --title "Tune model parameters nr 1" --body "Gate failure test, then fix"
```

In a dedicated terminal, watch the PR run, and confirm that `train-and-evaluate` fails at the "Evaluate and gate" step:

```powershell
$runId = gh run list --repo GiuseppePiscopo/gp-mlops-fundamentals --workflow ml-pipeline.yml --branch experiment/tune-model-1 --limit 1 --json databaseId --jq ".[0].databaseId"

gh run watch $runId --repo GiuseppePiscopo/gp-mlops-fundamentals

gh run view $runId --repo GiuseppePiscopo/gp-mlops-fundamentals --log-failed | Select-Object -Last 8
```

Confirm that the PR check failed (don't merge the PR), that no new model version was registered, and that the deployed model hasn't changed:

```powershell
gh pr checks experiment/tune-model-1 --repo GiuseppePiscopo/gp-mlops-fundamentals
```

```cmd
az ml model list --name gp-mof-capstone-model --query "[].{version:version, stage:tags.stage}" -o table

az ml online-deployment show --name blue --endpoint-name gp-mof-capstone-endpoint --query model -o tsv
```

### Restore the model

Fix the same PR with parameters that pass the gate (`n_estimators=300`, `max_depth=20` gives `R2` of about `0.86`). Pushing to the PR branch restarts the check:

```powershell
(Get-Content .\pipelines\gp-mof-capstone-job-rf.yml) -replace 'n_estimators: 50', 'n_estimators: 300' -replace 'max_depth: 5', 'max_depth: 20' | Set-Content .\pipelines\gp-mof-capstone-job-rf.yml

git commit -am "fix(repo): usa parametri che superano il gate"

git push github experiment/tune-model-1
```

In a dedicated terminal, watch the new PR run (the latest one for the branch, not the failed one) until it passes:

```powershell
$runId = gh run list --repo GiuseppePiscopo/gp-mlops-fundamentals --workflow ml-pipeline.yml --branch experiment/tune-model-1 --limit 1 --json databaseId --jq ".[0].databaseId"

gh run watch $runId --repo GiuseppePiscopo/gp-mlops-fundamentals

gh pr checks experiment/tune-model-1 --repo GiuseppePiscopo/gp-mlops-fundamentals
```

Merge the PR:

```powershell
gh pr merge experiment/tune-model-1 --repo GiuseppePiscopo/gp-mlops-fundamentals --squash --admin --delete-branch
```

Sync the local `main` and delete the branch:

```powershell
git switch main

git pull github main

git branch -D experiment/tune-model-1
```

In a dedicated terminal, watch the run started by the merge until `deploy` waits for approval, which confirms that the gate passed:

```powershell
$runId = gh run list --repo GiuseppePiscopo/gp-mlops-fundamentals --workflow ml-pipeline.yml --event push --limit 1 --json databaseId --jq ".[0].databaseId"

gh run watch $runId --repo GiuseppePiscopo/gp-mlops-fundamentals
```

### Approve the deployment

Approve the pending deployment:

```powershell
$runId = gh run list --repo GiuseppePiscopo/gp-mlops-fundamentals --workflow ml-pipeline.yml --limit 1 --json databaseId --jq ".[0].databaseId"

$envId = [long](gh api repos/GiuseppePiscopo/gp-mlops-fundamentals/environments/production --jq .id)

@{ environment_ids = @($envId); state = "approved"; comment = "Approved" } | ConvertTo-Json -Compress | gh api --method POST repos/GiuseppePiscopo/gp-mlops-fundamentals/actions/runs/$runId/pending_deployments --input -
```

The watch in the dedicated terminal ends when the run completes.

### Verify the production model

Check that the model tagged `production` is the one served by the blue deployment, and test the endpoint:

```cmd
az ml model list --name gp-mof-capstone-model --query "[].{version:version, stage:tags.stage, job:tags.job, git_sha:tags.git_sha}" -o table

az ml online-deployment show --name blue --endpoint-name gp-mof-capstone-endpoint --query model -o tsv

az ml online-endpoint invoke --name gp-mof-capstone-endpoint --deployment-name blue --request-file data\test-request\request.json
```

In Azure ML Studio, open the `gp-mof-capstone-model` model and confirm that the "Production" version matches the deployment model and the workflow job (`job` tag).

### Roll back to the previous model version

Find the version currently in production and the previous one (the most recent `archived` version):

```cmd
az ml model list --name gp-mof-capstone-model --query "[].{version:version, stage:tags.stage, job:tags.job}" -o table
```

Promote the previous version again, archive the current one, and point the blue deployment to the previous version:

```cmd
az ml model update --name gp-mof-capstone-model --version <CURRENT_VERSION> --set tags.stage=archived

az ml model update --name gp-mof-capstone-model --version <PREVIOUS_VERSION> --set tags.stage=production

az ml online-deployment update --name blue --endpoint-name gp-mof-capstone-endpoint --set model=azureml:gp-mof-capstone-model:<PREVIOUS_VERSION>
```

Confirm that the endpoint serves the previous model:

```cmd
az ml online-deployment show --name blue --endpoint-name gp-mof-capstone-endpoint --query model -o tsv

az ml online-endpoint invoke --name gp-mof-capstone-endpoint --deployment-name blue --request-file data\test-request\request.json
```

## Part 8: Cleanup

### Remove the remote endpoint

Delete the endpoint; this also removes its blue deployment:

```cmd
az ml online-endpoint delete --name gp-mof-capstone-endpoint --yes
```

### Reduce the access exposure

To keep the GitHub Actions access for future runs with less exposure, remove only the `Contributor` role assignment: the app registration, federated credentials and GitHub secrets stay, but the workflow can't use any Azure resource.

```powershell
$appId = az ad app list --display-name "gp-mof-capstone-app-ghactions" --query "[0].appId" -o tsv

$subscriptionId = az account show --query id -o tsv

az role assignment delete --assignee $appId --role contributor --scope "/subscriptions/$subscriptionId/resourceGroups/gp-mof-rg-dev"
```

Verify that no role assignment is left:

```powershell
az role assignment list --assignee $appId --scope "/subscriptions/$subscriptionId/resourceGroups/gp-mof-rg-dev" -o table
```

### Restore the access for GitHub Actions

Before a new run, assign the role again:

```powershell
$appId = az ad app list --display-name "gp-mof-capstone-app-ghactions" --query "[0].appId" -o tsv

$subscriptionId = az account show --query id -o tsv

az role assignment create --assignee $appId --role contributor --scope "/subscriptions/$subscriptionId/resourceGroups/gp-mof-rg-dev"
```

Then recreate the endpoint as in "Recreate the managed online endpoint" in Part 1, and the blue deployment as in "Create the blue deployment" in Part 5.

### Remove the Azure access for GitHub Actions

To remove the access completely instead, delete the role assignment (skip it if already removed above), then the app registration; this also removes its federated credentials and service principal. Set `$appId` and `$subscriptionId` as in "Reduce the access exposure" if the terminal is new:

```powershell
az role assignment delete --assignee $appId --role contributor --scope "/subscriptions/$subscriptionId/resourceGroups/gp-mof-rg-dev"

az ad app delete --id $appId
```

To recreate it, repeat Part 3: the app registration gets a new client ID, so update the `AZURE_CLIENT_ID` secret in "Create the GitHub secrets".
