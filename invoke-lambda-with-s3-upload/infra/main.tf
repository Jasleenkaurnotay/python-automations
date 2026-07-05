module "network" {
  source          = "./modules/network"
  vpc_cidr        = var.vpc_cidr
  vpc_name        = var.vpc_name
  pvt_subnet_data = var.pvt_subnet_data
  project_name    = var.project_name
  aws_region      = var.aws_region
}

module "rds" {
  source         = "./modules/rds"
  db_server_name = var.db_server_name
  db_name        = var.db_name
  db_user        = var.db_user
  db_pwd         = var.db_pwd
  project_name   = var.project_name
  vpc_id         = module.network.vpc_id
  pvt_sub_ids    = module.network.pvt_sub_ids
}

module "s3" {
  source       = "./modules/s3"
  project_name = var.project_name
}

module "lambda" {
  source          = "./modules/lambda"
  project_name    = var.project_name
  db_server_name  = var.db_server_name
  db_name         = var.db_name
  db_user         = var.db_user
  db_pwd          = var.db_pwd
  vpc_id          = module.network.vpc_id
  pvt_sub_ids     = module.network.pvt_sub_ids
  rds_endpoint    = module.rds.rds_endpoint
  lambda_zip_path = var.lambda_zip_path
  s3_bucket_arn   = module.s3.s3_bucket_arn
  db_secret_arn   = module.secrets.db_secret_arn
}

module "secrets" {
  source       = "./modules/secrets"
  project_name = var.project_name
  db_pwd       = var.db_pwd
}

# Create notification configuration for Lambda function
resource "aws_s3_bucket_notification" "notify_lambda" {
  bucket = module.s3.s3_bucket_id

  lambda_function {
    lambda_function_arn = module.lambda.lambda_func_arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".csv"
  }

  depends_on = [module.lambda] # depends_on can only reference the whole module, not a resource inside it

}

# Allow Lambda SG to reach RDS on Postgres port
resource "aws_security_group_rule" "rds_allow_lambda" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = module.rds.rds_sg_id       # RDS module's SG — needs an output if not already exposed
  source_security_group_id = module.lambda.lambda_sg_id # Lambda module's SG — needs an output if not already exposed
}