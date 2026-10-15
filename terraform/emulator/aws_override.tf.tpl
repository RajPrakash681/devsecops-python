# LOCAL EMULATOR ONLY - copied into terraform/ as moto_override.tf by emulator/run.sh and removed
# again when it exits (*_override.tf is git-ignored). Terraform merges an *_override.tf file into
# the matching block of the main config: this one adds dummy credentials and sends every AWS API
# call to a moto server in Docker. Without this file the same code targets real AWS.
provider "aws" {
  access_key = "test"
  secret_key = "test"

  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true

  endpoints {
    ec2 = "http://localhost:5050"
    sts = "http://localhost:5050"
    iam = "http://localhost:5050"
    eks = "http://localhost:5050"
  }
}
