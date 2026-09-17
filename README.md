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
cd ./src

python -m ridge.train --training_data ../data/sample/ --alpha 1.0

python -m random_forest.train --training_data ../data/sample/ --n_estimators 100 --max_depth 10
```

Run these from inside the `src/` folder, since the `common` module is resolved relative to the current working directory.

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
