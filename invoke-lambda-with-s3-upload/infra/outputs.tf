output "s3_bucket_name" {
  value = module.s3.s3_bucket_id
}

output "lambda_function_name" {
  value = module.lambda.lambda_func_arn
}

output "rds_endpoint" {
  value = module.rds.rds_endpoint
}