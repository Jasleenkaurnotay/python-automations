output "tags" {
  value       = local.tags
  description = "Tags declared as local variable in root module"
}

output "cont_def_map" {
  value       = local.cont_def_map
  description = "Container definition input"
}