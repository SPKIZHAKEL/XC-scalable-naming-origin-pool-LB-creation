locals {

  domains_per_lb = [for key, value in var.batches : value]
  # eg 5
  #   no_of_routes = sum([for domain in var.domains : len(domain)])
  # eg [3,2] [0,1,2,3,4] len-
  #   no_of_domains_per_lb = [for domain in var.domains : len(domain)]


  flattened_domains = flatten(values(var.batches))
  origin_pool_names = var.origin_pool_names
  # var.hostname_cert_mapping
}


resource "volterra_http_loadbalancer" "tf-demo-lb" {
  for_each                        = var.batches
  name                            = each.key
  namespace                       = var.namespace
  advertise_on_public_default_vip = true
  disable_api_definition          = true
  domains                         = each.value
  
  https {
    http_redirect = true
    port          = 443
    tls_cert_params {
      tls_config {
        default_security = true
      }
      dynamic "certificates" {
        # for_each = var.hostname_cert_mapping
        for_each = var.cert_per_lb[each.key]
        content {
          name      = certificates.value
          # certificates.value[0]
          namespace = var.namespace
          tenant = var.tenant
        }
      }
    }
  }
  # labels = var.labels
  app_firewall {
    name      = "app-fw-monitoring"
    namespace = var.namespace #hard coding monitoring
    tenant = var.tenant
  }

  dynamic "routes" {

    for_each = each.value
    content {

      simple_route {
        path {
          prefix = "/"
        }
        headers {

          invert_match = false
          name         = "Host"

          exact = routes.value
        }
        http_method = "ANY"
        
        # incoming_port {
        #   port = 443
        # }
        origin_pools {
          pool {
            name = "${join("-", slice(split(".", routes.value), 0, 2))}-origin"
            # var.origin_pool_names[index(local.flattened_domains, routes.value)]

            namespace = var.namespace
            tenant = var.tenant

          }
        }
        disable_host_rewrite = true
        # advanced_options {
        #   inherited_waf = true
        #   waf_exclusion_policy {

        #   }
        # }
      }

    }
  }

  l7_ddos_protection {
    mitigation_block       = true
    default_rps_threshold  = true
    clientside_action_none = true
    ddos_policy_none       = true
  }

depends_on = [ module.app_firewall ]
}

module "app_firewall" {
  source       = "../app_firewall"
  names        = ["app-fw-monitoring", "app-fw-blocking"]
  namespace    = var.namespace
  app_fw_count = 2

  enforcement_mode = [{ monitoring = true, blocking = false }, { monitoring = false, blocking = true }]
}



