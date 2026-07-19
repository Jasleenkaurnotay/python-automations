variable "aws_region" {
    type = string
    description = "Enter the AWS region in which infrastructure is to be created"
}

variable "project_name" {
    type = string
    description = "Enter a project name that will be used as a prefix to name resources"
}

variable "vpc_cidr" {
    type = string
    description = "Enter the CIDR block of the VPC"
}

variable "pvt_sub_cidr" {
    type = list(string)
    description = "Enter the list of CIDR blocks for the number of private subnets required in the VPC"
}

variable "pub_sub_cidr" {
    type = list(string)
    description = "Enter the list of CIDR blocks for the number of public subnets required in the VPC"
}

variable "tags" {
    type = map(string)
    description = "Tags declared as local variable in root module"
}