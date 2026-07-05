# Create Security group
resource "aws_security_group" "db_sg" {
    name = "postgres-rds-sg"
    vpc_id = var.vpc_id
    tags = {
        Name = "${var.project_name}-db-sg"
        Managed_By = "Terraform"
    }
}

# Create security group rule for RDS in root's main.tf since lambda function should be created first for this block to create correctly

# Create DB subnet group
resource "aws_db_subnet_group" "db_sub_grp" {
    name = "db-sub-grp"
    # Reference a list of your private subnet IDs
    subnet_ids = var.pvt_sub_ids
}

# Create Instance
resource "aws_db_instance" "db" {
    identifier = var.db_server_name
    allocated_storage = 20
    db_name = var.db_name
    engine = "postgres"
    engine_version = "17"
    instance_class = "db.t3.micro"
    db_subnet_group_name = aws_db_subnet_group.db_sub_grp.name
    username = var.db_user
    password = var.db_pwd
    vpc_security_group_ids = [aws_security_group.db_sg.id]
    apply_immediately = true
    skip_final_snapshot = true
}