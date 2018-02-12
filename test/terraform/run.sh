#!/bin/bash


if [[ $1 == "apply" ]]; then
  set -x
  terraform init
  terraform apply -var 'vpc_id=vpc-0d197965' -auto-approve=true

elif [[ $1 == "delete" ]] || [[ $1 == "destroy" ]]; then
  set -x
  terraform destroy -var 'vpc_id=vpc-0d197965' -force
  set +x
  ONPREMASSC=$(aws ssm describe-instance-information  --filters "Key=IamRole,Values=sshless-role-onprem" | jq -r '.InstanceInformationList[].InstanceId')

  for ASSOC in ${ONPREMASSC}; do
    echo "deregister-managed-instance: ${ASSOC}"
    aws ssm deregister-managed-instance --instance-id "${ASSOC}"
  done

elif [[ $1 == "web" ]] || [[ $1 == "app" ]]; then
  set -x
  sshless cmd -f tag:Role=$1 hostname

elif [[ $1 == "web-role" ]]; then

  SERVICEROLE=$(terraform output sshless-role-webrole)
  echo "executing SSHLess comand with service role with tag Role=web"
  set -x
  sshless --iam ${SERVICEROLE} cmd -f tag:Role=web hostname
  set +x

  echo "executing SSHLess comand with service role with tag Role=app"
  echo "expected to failed"
  set -x
  sshless --iam ${SERVICEROLE} cmd -f tag:Role=app hostname


elif [[ $1 == "legacy" ]]; then

  ONPREM=$(aws ssm describe-instance-information --instance-information-filter-list "key=ResourceType,valueSet=ManagedInstance" | jq -r '.InstanceInformationList | map(.InstanceId) | join(",")')
  echo "Query using ID (Tags not available on prem) ID: ${ONPREM}"
  set -x
  sshless cmd -i ${ONPREM} hostname

elif [[ $1 == "parameter" ]]; then
  echo "EC2 reading Parameter Store"
  set -x
  sshless cmd -f tag:Purpose=sshless "echo {{ssm:example.parameter}}"
  set +x

  echo "OnPrem reading Parameter Store"
  ONPREM=$(aws ssm describe-instance-information --instance-information-filter-list "key=ResourceType,valueSet=ManagedInstance" | jq -r '.InstanceInformationList | map(.InstanceId) | join(",")')
  echo "Query using ID (Tags not available on prem) ID: ${ONPREM}"

  set -x
  sshless cmd -i ${ONPREM} "echo {{ssm:example.parameter}}"
else
  echo "MISSING Action: ./run.sh apply | destroy | web | app | web-role | legacy | parameter"
fi
