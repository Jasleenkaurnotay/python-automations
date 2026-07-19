output "ecs_cluster_id" {
    value = aws_ecs_cluster.ecs_cluster.id
}

output "scan_task_def_arn" {
    value = aws_ecs_task_definition.task_defs["scan"].arn
    description = "ARN of scan-task-definition"
}