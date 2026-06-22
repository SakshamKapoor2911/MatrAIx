terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }

  # Remote state is recommended before any team use. Left commented until the
  # account + bucket exist (see README-DEPLOY.md).
  # backend "s3" {
  #   bucket = "mircoverse-tfstate"
  #   key    = "platform/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "MircoVerse"
      ManagedBy = "Terraform"
      Phase     = "platform"
    }
  }
}
