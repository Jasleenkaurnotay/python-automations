variable "project_name" {
    type = string
    description = "Enter a project name that will be used as a prefix to name resources"
}

variable "ecs_cluster_id" {
    type = string
    description = "ECS cluster ID"
}

variable "scan_task_def_arn" {
    type = string
    description = "ARN of scan-task-def"
}

variable "pvt_sub_ids" {
    type = list(string)
    description = "Private subnet IDs of the VPC"
}

variable "sqs_queue_name" {
    type = string
    description = "Name of the SQS queue driving scan-task autoscaling"
    default = "clamav-scanner-queue"
}

variable "scan_task_sg_id" {
  type        = string
  description = "Security group ID for the scan ECS task"
}