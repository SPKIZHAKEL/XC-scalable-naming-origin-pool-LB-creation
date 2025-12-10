module "https_custom_lb" {
  source = "./modules/https_custom_lb"
  providers = {
    volterra = volterra
  }
  lb_count   = length(var.batches)
  namespace  = var.namespace
  tenant_url = var.tenant_url
  api_token  = var.api_token
  # labels     = var.labels

  batches               = var.batches
  certificate_names     = var.certificate_names
  hostname_cert_mapping = var.hostname_cert_mapping
  origin_classification = var.origin_classification
  origin_pool_dict      = var.origin_pool_dict
  origin_pool_names     = var.origin_pool_names
  depends_on            = [module.origin_pool]
  cert_per_lb = var.cert_per_lb
  tenant = var.tenant
}

module "origin_pool" {
  source                = "./modules/origin_pool"
  namespace             = var.namespace
  origin_classification = var.origin_classification
  origin_pool_dict      = var.origin_pool_dict
  origin_pool_names     = var.origin_pool_names
  tenant = var.tenant
}

# output "https_custom_lb_output" {
#   value = module.https_custom_lb.cname

#   description = "attributes of http custom lb"
# }


output "custom_lb_list" {
  value       = module.https_custom_lb.lb-list
  description = "list of all LBs in namespace (custom output)"
}




