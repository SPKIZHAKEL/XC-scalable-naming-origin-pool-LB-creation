resource "volterra_app_firewall" "app_fw" {
  count                     = var.app_fw_count
  name                      = var.names[count.index]
  namespace                 = var.namespace
  allow_all_response_codes  = true
  use_default_blocking_page = true

  default_detection_settings = true

  blocking   = var.enforcement_mode[count.index]["blocking"]
  monitoring = var.enforcement_mode[count.index]["monitoring"]
}
