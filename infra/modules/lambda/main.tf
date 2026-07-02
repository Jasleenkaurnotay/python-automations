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
  name              = "/aws/lambda/"aws_lambda_function.lambda_func.name
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

# Attach cloudwatch logging policy to lambda role
resource "aws_iam_role_policy_attachment" "lambda_perms" {
    role = aws_iam_role.lambda_iam_role.name
    policy_arn = aws_iam_policy.cloudwatch_logging_perm.arn
}

# Create lambda function
resource "aws_lambda_function" "lambda_func" {
    function_name = "${var.project_name}-lambda"
    role = aws_iam_role.lambda_iam_role.arn
    runtime = "python3.13"
    vpc_config {
      subnet_ids = var.pvt_sub_ids
      security_group_ids = aws_security_group.lambda_sg.id
    }
    ephemeral_storage {
      size = 512
    }

    depends_on = [ 
        aws_iam_role.lambda_iam_role
        aws_cloudwatch_log_group.laws_cloudwatch_log_group.lambda_cloudwatch_grp
    ]
}