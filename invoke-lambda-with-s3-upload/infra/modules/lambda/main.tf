# Create Security group
resource "aws_security_group" "lambda_sg" {
    name = "lambda-rds-sg"
    vpc_id = var.vpc_id
    tags = {
        Name = "${var.project_name}-lambda-sg"
        Managed_By = "Terraform"
    }
}

# Create custom IAM role for Lambda
resource "aws_iam_role" "lambda_iam_role" {
    name = "${var.project_name}-lambda"
    assume_role_policy = <<EOF
    {
    "Version": "2012-10-17",
    "Statement": [
        {
        "Action": "sts:AssumeRole",
        "Principal": {
            "Service": "lambda.amazonaws.com"
        },
        "Effect": "Allow",
        "Sid": ""
        }
    ]
    }
    EOF
}

# Create cloudwatch log group
resource "aws_cloudwatch_log_group" "lambda_cloudwatch_grp" {
  name              = "/aws/lambda/${var.project_name}-lambda"
  retention_in_days = 1
}

# Create IAM policy for Lambda logging
resource "aws_iam_policy" "cloudwatch_logging_perm" {
    name = "lambda-cloudwatch-logging"
    path = "/"
    policy = <<EOF
    {
    "Version": "2012-10-17",
    "Statement": [
        {
        "Action": [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
        ],
        "Resource": "arn:aws:logs:*:*:*",
        "Effect": "Allow"
        }
    ]
    }
    EOF
}

# Define the IAM policy for S3 read-only access
resource "aws_iam_policy" "lambda_s3_ro_pol" {
    name = "lambda-s3-pol"
    policy =  jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        # Restrict access to only this bucket and its contents
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      }
    ]
  })
}

# Define IAM policy for lambda to fetch secret from secret manager
resource "aws_iam_policy" "lambda_db_sec_pol" {
  name = "lambda-db-secret-pol"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = var.db_secret_arn
      }
    ]
  })
}

# Attach cloudwatch logging policy to lambda role
resource "aws_iam_role_policy_attachment" "lambda_log_perms" {
    role = aws_iam_role.lambda_iam_role.name
    policy_arn = aws_iam_policy.cloudwatch_logging_perm.arn
}

# Attach S3 read only policy to lambda role
resource "aws_iam_role_policy_attachment" "lambda_s3_perms" {
    role = aws_iam_role.lambda_iam_role.name
    policy_arn = aws_iam_policy.lambda_s3_ro_pol.arn
}

# Attach aws-managed VPC access policy to lambda role
resource "aws_iam_role_policy_attachment" "lambda_vpc_perms" {
    role = aws_iam_role.lambda_iam_role.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Attach IAM policy to allow lambda to get secret from secret manager
resource "aws_iam_role_policy_attachment" "lambda_sec_mgr_perms" {
  role = aws_iam_role.lambda_iam_role.name
  policy_arn = aws_iam_policy.lambda_db_sec_pol.arn
}

# Create lambda function
resource "aws_lambda_function" "lambda_func" {
    function_name = "${var.project_name}-lambda"
    role = aws_iam_role.lambda_iam_role.arn
    handler = "lambda_function.lambda_handler"
    runtime = "python3.13"
    filename = var.lambda_zip_path
    # attach lambda layer
    layers = [aws_lambda_layer_version.psycopg2_layer.arn]
    vpc_config {
      subnet_ids = var.pvt_sub_ids
      security_group_ids = [aws_security_group.lambda_sg.id]
    }
    ephemeral_storage {
      size = 512
    }

    # Define env variables here
    environment {
      variables = {
        DB_HOST = var.rds_endpoint
        DB_PORT = "5432"
        DB_NAME = var.db_name
        DB_USER = var.db_user
        DB_SECRET_ARN = var.db_secret_arn
      }
    }

    depends_on = [ 
        aws_iam_role.lambda_iam_role,
        aws_cloudwatch_log_group.lambda_cloudwatch_grp
    ]
}


# Allow Lambda permission to query S3
resource "aws_lambda_permission" "allow_s3_invoke" {
    statement_id = "AllowS3Invoke"
    action = "lambda:InvokeFunction"
    function_name = aws_lambda_function.lambda_func.function_name
    principal = "s3.amazonaws.com"
    source_arn = var.s3_bucket_arn
}

# Install lambda layer for pycopg2 library
resource "aws_lambda_layer_version" "psycopg2_layer" {
  filename = "${path.module}/../../../scripts/lambda-layer/layer.zip"
  layer_name = "psycopg2-layer"
  compatible_runtimes = ["python3.13"]
  source_code_hash = filebase64sha256("${path.module}/../../../scripts/lambda-layer/layer.zip")
}