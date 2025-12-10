variable "names" {
  type = list(string)
}
variable "namespace" {
  type = string
}

variable "app_fw_count" {
  type = number
}

variable "enforcement_mode" {
  type = list(object({
    monitoring = bool
    blocking   = bool
  }))

}