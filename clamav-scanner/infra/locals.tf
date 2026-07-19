locals {
  tags = {
    ManagedBy = "Terraform"
    Purpose   = "Clamav-setup"
  }

  cont_def_map = {
    for cd in var.cont_def : cd.name => cd
  }
}