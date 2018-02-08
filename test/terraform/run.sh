#!/bin/bash


if [ $1 == "apply" ]; then
  set -x
  terraform apply -var 'vpc_id=vpc-0d197965' -auto-approve=true

elif [ $1 == "delete" ] || [ $1 == "destroy" ]; then
  set -x
  terraform destroy -var 'vpc_id=vpc-0d197965' -force

elif [ $1 == "web" ] || [ $1 == "app" ]; then
  set -x
  sshless cmd -f tag:Role=$1 hostname


elif [ $1 == "legacy" ]; then
  set -x
  ONPREM=$(aws ssm describe-instance-information --instance-information-filter-list "key=ResourceType,valueSet=ManagedInstance" | jq -r '.InstanceInformationList | map(.InstanceId) | join(",")')
  echo "Query using ID (Tags not available on prem) ID: ${ONPREM}"
  sshless cmd -i ${ONPREM} hostname

elif [ $1 == "parameter" ]; then
  echo "EC2 reading Parameter Store"
  set -x
  sshless cmd -f tag:Purpose=sshless "echo {{ssm:example.parameter}}"

  echo "OnPrem reading Parameter Store"
  ONPREM=$(aws ssm describe-instance-information --instance-information-filter-list "key=ResourceType,valueSet=ManagedInstance" | jq -r '.InstanceInformationList | map(.InstanceId) | join(",")')
  echo "Query using ID (Tags not available on prem) ID: ${ONPREM}"
  sshless cmd -i ${ONPREM} "echo {{ssm:example.parameter}}"
fi
