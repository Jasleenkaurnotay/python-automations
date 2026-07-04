output "rds_endpoint" {
    description = "Connection endpoint for RDS instance"
    value = aws_db_instance.db.endpoint
}

output "rds_sg_id" {
    value = aws_security_group.db_sg.id
}