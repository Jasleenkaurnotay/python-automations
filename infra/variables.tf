variable "aws_region" {
    type = string
    description = "Region to be used for AWS deployments"
    default = "us-east-1"
}

variable "project_name" {
    type = string
    description = "Name of the project"
}
## User needs to provide:
# CIDR range
# vpc name
# No. of pvt subnets needed

variable "vpc_cidr" {
    type = string
    description = "CIDR block for the VPC"
}

variable "vpc_name" {
    type = string
    description = "Prefix for the vpc"
}

variable "pvt_subnet_data" {
    type = list(object({
        cidr = string
        name = string
    }))
    description = "Private subnet data"
}

# variables for RDS module
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