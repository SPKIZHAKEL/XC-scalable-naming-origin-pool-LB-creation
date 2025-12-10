output "app_fw_id" {

  value = [for app_fw in volterra_app_firewall.app_fw : app_fw.id]
}

output "app_fw_name" {
  value = volterra_app_firewall.app_fw[*].name
}