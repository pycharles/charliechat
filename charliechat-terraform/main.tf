terraform {
  required_version = ">= 1.13.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.14.0"
    }
    dotenv = {
      source  = "jrhouston/dotenv"
      version = ">= 1.0.1"
    }
  }
}

# Load environment variables from .env file
data "dotenv" "env" {
  filename = "../.env"
}

provider "aws" {
  region = data.dotenv.env.env["AWS_REGION"]
}