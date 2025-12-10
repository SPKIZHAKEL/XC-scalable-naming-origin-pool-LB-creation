resource "volterra_origin_pool" "example" {
  for_each = var.origin_pool_dict
  name     = each.key
  namespace              = var.namespace
  endpoint_selection     = "Local Endpoints Preferred"
  loadbalancer_algorithm = "Load Balancer Override"
  dynamic "origin_servers" {

    for_each = each.value[1] == "private_name" ? [1] : []
    content {
      private_name {
        dns_name = each.value[0]



        outside_network = true
        site_locator {

          virtual_site {
            name      = "placeholder"
            namespace = "placeholder"
            tenant = var.tenant
          }

        }
        segment {

        }

      }
    }
  }

  dynamic "origin_servers" {
    for_each = each.value[1] == "private_ip" ? split(" ", each.value[0]) : []
    content {
      private_ip {
        ip = origin_servers.value




        outside_network = true
        site_locator {

          virtual_site {
              name      = "placeholder"
            namespace = "placeholder"

          }

        }
        segment {

        }

      }
    }
  }



  port = "443"



  use_tls {
    tls_config {
      default_security = true
    }
  }
}