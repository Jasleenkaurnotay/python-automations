output "sqs_queue_name" {
    value = aws_sqs_queue.sqs_queue.name
}

output "sqs_queue_arn" {
    value = aws_sqs_queue.sqs_queue.arn
}

output "upload_bucket_name" {
    value = aws_s3_bucket.upload_bucket.bucket
}

output "clean_bucket_name" {
    value = aws_s3_bucket.clean_bucket.bucket
}

output "db_bucket_name" {
    value = aws_s3_bucket.db_bucket.bucket
}

output "sns_topic_arn" {
    value = aws_sns_topic.dirty_file_topic.arn
}