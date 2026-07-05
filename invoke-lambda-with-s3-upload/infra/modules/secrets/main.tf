# Create Secrets manager secret
resource "aws_secretsmanager_secret" "db_pwd" {
    name = "${var.project_name}-db-pwd"
}

resource "aws_secretsmanager_secret_version" "db_password_version" {
    secret_id = aws_secretsmanager_secret.db_pwd.id
    secret_string = jsonencode({
    password = var.db_pwd
  })
}