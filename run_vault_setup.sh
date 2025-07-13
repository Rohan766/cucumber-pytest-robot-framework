#!/bin/bash

# Set Vault address
export VAULT_ADDR=https://civ1.dv.adskengineer.net

# Login to Vault using OIDC
vault login -method oidc

# Run the AWS credentials generation script
./generate_aws_credentials-stage\ 2\ copy.sh 