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

## Set Azure resource group and ML workspace as default

This lab project assumes that Azure resource group and an Azure Machine Learning workspace already exist. They're named `gp-mof-rg-dev` and `gp-mof-ws-dev`.  
Set the resource group and ML workspace as the default to avoid specifying them on every command:

```cmd
az configure --defaults group=gp-mof-rg-dev workspace=gp-mof-ws-dev
```

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
python ./src/train_ridge.py --training_data ./data/sample/ --alpha 1.0

python ./src/train_rf.py --training_data ./data/sample/ --n_estimators 100 --max_depth 10
```
