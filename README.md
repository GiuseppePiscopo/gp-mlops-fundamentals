# Lab project: MLOps Fundamentals training milestone

Problem: bike sharing demand prediction  
Dataset: Seoul Bike Sharing dataset from Kaggle (https://www.kaggle.com/datasets/joebeachcapital/seoul-bike-sharing)

## Prerequisites

Confirm the Azure Machine Learning extension is installed with the following command:

```cmd
az extension list -o table
```

Install the Python dependencies required to run the scripts locally:

```cmd
pip install -r ./requirements.txt
```

### Docker Desktop settings for local endpoints

Testing a managed endpoint locally (Phase 2) runs it in a Docker container, and on some networks pulling the Microsoft base image fails unless you apply these one-time Docker Desktop settings.

Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) (WSL2 backend) if not already present.

Disable the containerd image store: Docker Desktop → Settings → General → uncheck "Use containerd for pulling and storing images" → Apply & Restart.

Pin `mcr.microsoft.com` to its IPv4 address in the hosts file (some networks fail the IPv6 TLS handshake to this host); run as Administrator:

```powershell
$ip = (Resolve-DnsName mcr.microsoft.com -Type A | Select-Object -First 1).IPAddress
Add-Content -Path "$env:SystemRoot\System32\drivers\etc\hosts" -Value "`n$ip`tmcr.microsoft.com"
```

## Register providers for managed online endpoints

Before Phase 2 creates a managed online endpoint, confirm that these resource providers are registered in the Azure subscription:

```cmd
az provider show --namespace Microsoft.Web --query registrationState -o tsv

az provider show --namespace Microsoft.Cdn --query registrationState -o tsv

az provider show --namespace Microsoft.PolicyInsights --query registrationState -o tsv
```

Each command must return `Registered`. If it returns `NotRegistered`, register that provider and wait for registration to complete:

```cmd
az provider register --namespace Microsoft.Web

az provider register --namespace Microsoft.Cdn

az provider register --namespace Microsoft.PolicyInsights
```

The Azure ML endpoint creation error may report the provider as `[N/A]`. In this lab subscription, registering these providers resolved that error. These are additional to the standard providers already used by the Azure ML workspace, such as Microsoft.MachineLearningServices, Microsoft.Storage, Microsoft.ContainerRegistry, and Microsoft.KeyVault.

## Set Azure resource group and ML workspace as default

This lab project assumes that Azure resource group and an Azure Machine Learning workspace already exist. They're named `gp-mof-rg-dev` and `gp-mof-ws-dev`.  
Set the resource group and ML workspace as the default to avoid specifying them on every command:

```cmd
az configure --defaults group=gp-mof-rg-dev workspace=gp-mof-ws-dev
```

## Phase 1 Lab

See [Phase 1 Lab instructions](docs/phase1-lab-instructions.md) for detailed steps on that phase.

## Phase 2 Lab

See [Phase 2 Lab instructions](docs/phase2-lab-instructions.md) for detailed steps on that phase.

## Phase 3 Lab

Requires the [GitHub CLI](https://cli.github.com/) authenticated with `gh auth login`.

See [Phase 3 Lab instructions](docs/phase3-lab-instructions.md) for detailed steps on that phase.

## Known environment limitations

- **Model monitoring cannot run (Phase 2, Step 3) in this subscription because of the Italy North ESv3 quota.** The monitoring Spark job requires ESv3 SKUs, ESv3 is a legacy series, and the region refuses additional `standardESv3Family` quota. The monitor can be created and scheduled, but its Spark run fails. See the note in [Phase 2 Lab instructions](docs/phase2-lab-instructions.md).
