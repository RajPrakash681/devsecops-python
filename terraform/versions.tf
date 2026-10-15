terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# Credentials come from the environment (aws configure / AWS_PROFILE / SSO) - never from this repo.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "clinicflow"
      ManagedBy = "terraform"
      Owner     = var.owner
    }
  }
}
