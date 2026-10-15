#!/usr/bin/env bash
# the real AWS CLI, pointed at the local moto endpoint with dummy credentials
AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=ap-south-1 exec aws --endpoint-url http://localhost:5050 "$@"
