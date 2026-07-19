module "network" {
  source       = "./network"
  aws_region   = var.aws_region
  project_name = var.project_name
  vpc_cidr     = var.vpc_cidr
  pvt_sub_cidr = var.pvt_sub_cidr
  pub_sub_cidr = var.pub_sub_cidr
  tags         = local.tags
}

module "ecs" {
  source       = "./ecs"
  aws_region   = var.aws_region
  project_name = var.project_name
  tags         = local.tags
  cont_def_map = local.cont_def_map
}

module "autoscaling" {
  source            = "./autoscaling"
  project_name      = var.project_name
  ecs_cluster_id    = module.ecs.ecs_cluster_id
  scan_task_def_arn = module.ecs.scan_task_def_arn
  pvt_sub_ids       = module.network.pvt_sub_ids
  scan_task_sg_id   = module.network.scan_task_sg_id
  sqs_queue_name    = module.s3-sqs.sqs_queue_name
}

module "s3-sqs" {
  source       = "./s3-sqs"
  project_name = var.project_name
  tags         = local.tags
  alert_email  = var.alert_email
}