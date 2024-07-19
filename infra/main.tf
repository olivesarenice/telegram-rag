terraform {
  backend "s3" {
    bucket  = "oqsw-terraform-states"
    key     = "telegram-rag/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }

  required_providers {
    astra = {
      source  = "datastax/astra"
      version = "2.2.8"
    }

    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.0"
    }
  }
}
