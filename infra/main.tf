module "network" {
    source = "./modules/network"
    vpc_cidr = var.vpc_cidr
    vpc_name = var.vpc_name
    pvt_subnet_data = var.pvt_subnet_data
    project_name = var.project_name
    aws_region = var.aws_region
}

module "rds" {
    source = "./modules/rds"
    db_server_name = var.db_server_name
    db_name = var.db_name
    db_user = var.db_user
    db_pwd = var.db_pwd
    project_name = var.project_name
    vpc_id = module.network.vpc_id
    pvt_sub_ids = module.network.pvt_sub_ids
}