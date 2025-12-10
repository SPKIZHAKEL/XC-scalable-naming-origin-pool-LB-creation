# output "cname" {
#   value = volterra_http_loadbalancer.tf-demo-lb[*].cname
# }

output "lb-list" {
  value = [for lb in local.all_lbs.items : lb.name]
}

# output "acme_challenge" {
#   value = { for index, cert in data.volterra_http_loadbalancer_state.cert_info : cert.name => cert.auto_cert_info[0].dns_records }
# }


output "flattened_domains" {
  value = local.flattened_domains
}

