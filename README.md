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
