## Creating locals list with task_role_Arns for use only within this module
locals {
  task_role_arns = {
    scan = aws_iam_role.scan_role.arn
    update = aws_iam_role.update_role.arn
  }
}

# Creare ECS cluster
resource "aws_ecs_cluster" "ecs_cluster" {
    name = "${var.project_name}-ecs-cluster"
    tags = merge({ Name = "${var.project_name}-ecs-cluster"}, var.tags)
}

# Create task definitions for scan and update activities
resource "aws_ecs_task_definition" "task_defs" {
    for_each = var.cont_def_map
    family = "${var.project_name}-${each.key}-tasf-def"
    requires_compatibilities = ["FARGATE"]
    network_mode = "awsvpc"
    cpu = "256"
    memory = "512"
    container_definitions = jsonencode([
    {
        "image": each.value.image
        "essential": true
        "command": each.value.cmd
        "environment": [ for k, v in each.value.env : { name = k, value = v } ]
        "logConfiguration" : {
            "logDriver" : "awslogs"
            "options" : {
                "awslogs-group": aws_cloudwatch_log_group.task_logs[each.key].name
                "awslogs-region": var.aws_region
                "awslogs-stream-prefix": each.key
            }
        }
    }
    ])
    runtime_platform {
      operating_system_family = "LINUX"
      cpu_architecture = "X86_64"
    }
    execution_role_arn = aws_iam_role.ecs_task_exec_role.arn
    task_role_arn = local.task_role_arns[each.key]
}

########################################################
# Create ecsTaskExecutionRole IAM role
resource "aws_iam_role" "ecs_task_exec_role" {
    name = "${var.project_name}-ecstask-execution-role"

    assume_role_policy = jsonencode({
        Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      },
    ]
  })
}

# Attach ecsTaskDefinition policy to the above role
resource "aws_iam_role_policy_attachment" "attach_ecs_task_exec" {
    role = aws_iam_role.ecs_task_exec_role.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Attach cloudwatch log group create permissions 
resource "aws_iam_role_policy" "cw_lg_perm" {
    name = "cloudwatch-lg-create-policy"
    role = aws_iam_role.ecs_task_exec_role.id

    policy = jsonencode({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents" ],
                "Resource": "*"
            }
        ]
    })
}

#######################################################
# Create IAM role for Scan task
resource "aws_iam_role" "scan_role" {
    name = "${var.project_name}-scan-role"
    assume_role_policy = jsonencode({
        Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
    })
}

# Attach S3 and SQS permissions to scan IAM role
resource "aws_iam_role_policy" "scan_policy" {
    name = "${var.project_name}-scan-policy"
    role = aws_iam_role.scan_role.id
    policy = jsonencode({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:*",
                    "s3-object-lambda:*"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "sqs:*"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "sns:*"
                ],
                "Resource": "*"
            }
        ]
    })
}

#######################################################
# Create IAM role for Update task

resource "aws_iam_role" "update_role" {
    name = "${var.project_name}-update-role"
    assume_role_policy = jsonencode({
        Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
    })
}

# Attach permissions to scan IAM role
resource "aws_iam_role_policy" "update_policy" {
    name = "${var.project_name}-update-policy"
    role = aws_iam_role.update_role.id
    policy = jsonencode({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:*",
                    "s3-object-lambda:*"
                ],
                "Resource": "*"
            }
        ]
    })
}

#################################################
# Create cloudwatch log group 
resource "aws_cloudwatch_log_group" "task_logs" {
  for_each          = var.cont_def_map
  name              = "/ecs/${var.project_name}-${each.key}"
  retention_in_days = 7
  tags              = merge({ Name = "${var.project_name}-${each.key}-logs" }, var.tags)
}