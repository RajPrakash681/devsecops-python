#!/usr/bin/env bash
# Run the real Terraform configuration against moto (an AWS API emulator) when no AWS account
# is available. Every resource, plan and state transition is genuine Terraform; only the API
# endpoint is local, so nothing is billed and nothing exists in a real AWS account.
#
#   terraform/emulator/run.sh init
#   terraform/emulator/run.sh plan -out=tfplan
#   terraform/emulator/run.sh apply tfplan
#   terraform/emulator/run.sh destroy -auto-approve
#   terraform/emulator/run.sh stop            # remove the moto container
set -euo pipefail
cd "$(dirname "$0")/.."
MOTO_IMAGE="${MOTO_IMAGE:-motoserver/moto:5.1.22}"

if [ "${1:-}" = "stop" ]; then docker rm -f clinicflow-moto >/dev/null && echo "moto stopped"; exit 0; fi

if ! docker ps --format '{{.Names}}' | grep -qx clinicflow-moto; then
  # Host port 5050: on macOS port 5000 belongs to AirPlay Receiver.
  # MOTO_IAM_LOAD_MANAGED_POLICIES: preload AWS managed policies (AmazonEKSClusterPolicy, ...),
  # otherwise every policy attachment fails with NoSuchEntity.
  docker run -d --name clinicflow-moto -p 5050:5000 -e MOTO_IAM_LOAD_MANAGED_POLICIES=true "$MOTO_IMAGE" >/dev/null
  until curl -fs localhost:5050/moto-api/ >/dev/null; do sleep 1; done
  echo "moto is up on http://localhost:5050 (dashboard: http://localhost:5050/moto-api/)"
fi

cp emulator/aws_override.tf.tpl moto_override.tf
trap 'rm -f moto_override.tf' EXIT
export AWS_EC2_METADATA_DISABLED=true
terraform "$@"
