resource "volterra_waf_exclusion_policy" "dummy_policy" {
  description = "dummy policy due to route creation issue without it"
  name        = "placeholder-exclusion-policy"
  namespace   = var.namespace

  waf_exclusion_rules {
    exact_value = "placeholder"
    any_path    = false
    metadata {
      name        = "placeholder-exclusion-rule"
      description = "dummy rule due to route creation issue without it"
    }
    waf_skip_processing = true
  }
}