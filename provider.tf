terraform {
  required_version = ">= 0.13.1"
  required_providers {
    volterra = {
      source  = "volterraedge/volterra"
      version = "~> 0.11.45"
    }
    http = {
      source  = "hashicorp/http"
      version = "3.5.0"
    }
  }
}

provider "volterra" {
  api_p12_file = "<path to your p12 file>"
  url          = var.tenant_url
}