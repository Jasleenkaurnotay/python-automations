# Create 3 clamav buckets

resource "aws_s3_bucket" "upload_bucket" {
    bucket = "${var.project_name}-upload"
    tags = merge({ Name = "${var.project_name}-upload"}, var.tags)
}

resource "aws_s3_bucket" "clean_bucket" {
    bucket = "${var.project_name}-clean"
    tags = merge({ Name = "${var.project_name}-clean"}, var.tags)
}

resource "aws_s3_bucket" "db_bucket" {
    bucket = "${var.project_name}-db"
    tags = merge({ Name = "${var.project_name}-db"}, var.tags)
}

# Create an sqs queue
resource "aws_sqs_queue" "sqs_queue" {
    name = "${var.project_name}-queue"
    message_retention_seconds = 86400
    visibility_timeout_seconds = 30
}

# Configure sqs queue to allow S3 bucket to send messages to it
resource "aws_sqs_queue_policy" "notify_sqs" {
    queue_url = aws_sqs_queue.sqs_queue.id

    policy = jsonencode({
        Version = "2012-10-17" 
        Statement = [{
        Effect = "Allow"
        Principal = {
            Service = "s3.amazonaws.com"
        }
        Action   = "SQS:SendMessage"
        Resource = aws_sqs_queue.sqs_queue.arn
        Condition = {
            ArnLike = {
            "aws:SourceArn" = aws_s3_bucket.upload_bucket.arn
            }
        }
        }]
    }) 
}

# Configure S3 uplaod bucket to trigger notification
resource "aws_s3_bucket_notification" "s3_notify_sqs" {
    bucket = aws_s3_bucket.upload_bucket.id

    queue {
      queue_arn = aws_sqs_queue.sqs_queue.arn
      events = ["s3:ObjectCreated:*"]
    }

    depends_on = [aws_sqs_queue_policy.notify_sqs]

}

# Creat SNS topic 
resource "aws_sns_topic" "dirty_file_topic" {
    name = "${var.project_name}-sns-topic"
}

resource "aws_sns_topic_subscription" "dirty_file_email" {
    topic_arn = aws_sns_topic.dirty_file_topic.arn
    protocol  = "email"
    endpoint  = var.alert_email
}

##########################################################################################################
# Clamav DB bucket S3 lifecycle rule
resource "aws_s3_bucket_lifecycle_configuration" "upload_bucket_life_conf" {
    bucket = aws_s3_bucket.upload_bucket.id 

    # Rule 1: Expire scanned uploads
    rule {
        id = "Expire 30 day old scanned files"
        status = "Enabled"

        filter {
          tag {
            key = "FILES_SCANNED"
            value = "true"
          }
        }

        # permanently delete scanned files on Day 31
        expiration {
            days = 30
        }
    }
}

# Clamav clean bucket lifecycle rule
resource "aws_s3_bucket_lifecycle_configuration" "clean_bucket_life_conf" {
    bucket = aws_s3_bucket.clean_bucket.id

    # Rule 1: Move scanned files to Intelligent tiering after 30 days
    rule {
        id = "tier-scanned-clean-files"
        status = "Enabled"

        filter {
            tag {
              key = "FILES_SCANNED"
              value = "true"
            }
        }

        transition {
          days = 30
          storage_class = "INTELLIGENT_TIERING"
        }
    }
}