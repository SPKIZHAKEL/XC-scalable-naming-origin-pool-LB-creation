variable "namespace" {
  type = string
}

# variable "cdn_domain" {
#   type = list(string)
# }
# variable "cdn_cname" {
#   type = list(string)
# }
# variable "labels" {
#   type = map(string)
# }

variable "origin_classification" {
  type = list(list(string))
}

variable "origin_pool_names" {
  type = list(string)
}
variable "origin_pool_dict" {
  type = map(list(string))
}
variable "tenant"{
  type = string
}