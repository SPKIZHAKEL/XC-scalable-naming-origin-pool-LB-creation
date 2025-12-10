variable "lb_count" {
  type = number
}
variable "namespace" {
  type = string
}
variable "tenant_url" {
  type = string
}
variable "api_token" {
  type      = string
  sensitive = true
}

# variable "labels" {
#   type = map(string)
# }


variable "batches" {
  type = map(list(string))
}
variable "origin_classification" {
  type = list(list(string))
}

variable "certificate_names" {
  type = list(string)
}

variable "origin_pool_names" {
  type = list(string)
}
variable "origin_pool_dict" {
  type = map(list(string))
}

variable "hostname_cert_mapping" {
  type = map(list(string))
}

variable "cert_per_lb" {
  type = map(list(string))
}

variable "tenant" {
  type = string
}
# variable "cdn_cname" {
#   type = list(string)
# }

# variable "cdn_domain" {
#   type = list(string)
# }

# variable "origin_pool_name_list" {
#   type = list(string)
# }
