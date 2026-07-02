variable "project_name" {
    type = string
    description = "Name of the project"
}

variable "db_server_name" {
    type = string
    description = "Name of RDS instance"
}

variable "db_name" {
    type = string
    description = "RDS DB name"
}

variable "db_user" {
    type = string
    description = "RDS database username"
}

variable "db_pwd" {
    type = string
    description = "RDS DB password"
}

variable "vpc_id" {
    type = string
    description = "AWS VPC ID"
}

variable "pvt_sub_ids" {
    type = list(string)
    description = "Private subnet IDs"
}