# Cloudwatch Metric alarm to scale up
resource "aws_cloudwatch_metric_alarm" "scan_msg_alarm" {
    alarm_name = "${var.project_name}-scan-msg-alarm"
    comparison_operator = "GreaterThanOrEqualToThreshold"
    evaluation_periods = 1
    metric_name = "ApproximateNumberOfMessagesVisible"
    namespace = "AWS/SQS"
    period = 60
    statistic = "Maximum"
    threshold = 1
    alarm_description = "Triggers when a message arrives in an SQS queue"

    dimensions = {
      QueueName = var.sqs_queue_name
    }

    alarm_actions = [ aws_appautoscaling_policy.scan_scale_up_pol.arn ]
}

# Cloudwatch metric alarm to scale down task
resource "aws_cloudwatch_metric_alarm" "scan_msg_alarm_zero" {
  alarm_name          = "${var.project_name}-scan-msg-zero-alarm"
  comparison_operator = "LessThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "Triggers when the queue is empty, to scale the scan service back to 0"

  dimensions = {
    QueueName = var.sqs_queue_name
  }

  alarm_actions = [aws_appautoscaling_policy.scan_scale_down_pol.arn]
}

# Define the Application Auto Scaling Target
resource "aws_appautoscaling_target" "scan_step_scale_target" {
    max_capacity = 2
    min_capacity = 0
    resource_id = aws_ecs_service.scan_svc.id
    scalable_dimension = "ecs:service:DesiredCount"
    service_namespace = "ecs"
}

# Define Step Scaling policy to scale up
resource "aws_appautoscaling_policy" "scan_scale_up_pol" {
    name = "${var.project_name}-scaleup-pol"
    policy_type = "StepScaling"
    resource_id = aws_appautoscaling_target.scan_step_scale_target.resource_id
    scalable_dimension = aws_appautoscaling_target.scan_step_scale_target.scalable_dimension
    service_namespace = aws_appautoscaling_target.scan_step_scale_target.service_namespace

    step_scaling_policy_configuration {
      adjustment_type = "ChangeInCapacity"
      cooldown = 30
      metric_aggregation_type = "Maximum"

      step_adjustment {
        metric_interval_lower_bound = 0
        metric_interval_upper_bound = 1
        scaling_adjustment = 1
      }

      step_adjustment {
        metric_interval_lower_bound = 1
        scaling_adjustment = 2
      }
    }
}

# Define Step Scaling policy to scale down tasks
resource "aws_appautoscaling_policy" "scan_scale_down_pol" {
  name               = "${var.project_name}-scaledown-pol"
  policy_type        = "StepScaling"
  resource_id        = aws_appautoscaling_target.scan_step_scale_target.resource_id
  scalable_dimension = aws_appautoscaling_target.scan_step_scale_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.scan_step_scale_target.service_namespace

  step_scaling_policy_configuration {
    adjustment_type         = "ExactCapacity"
    cooldown                = 30
    metric_aggregation_type = "Maximum"

    step_adjustment {
      metric_interval_upper_bound = 0
      scaling_adjustment          = 0
    }
  }
}

# Create AWS ECS service for scan task
resource "aws_ecs_service" "scan_svc" {
    name = "${var.project_name}-scan-svc"
    cluster = var.ecs_cluster_id
    task_definition = var.scan_task_def_arn
    desired_count = 0
    launch_type = "FARGATE"
    
    network_configuration {
      assign_public_ip = false
      subnets = var.pvt_sub_ids
      security_groups = [ var.scan_task_sg_id ]
    }
}