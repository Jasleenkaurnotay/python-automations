variable "aws_region" {
    type = string
    description = "Region to be used for AWS deployments"
    default = "us-east-1"
}

variable "project_name" {
    type = string
    description = "Name of the project"
}

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