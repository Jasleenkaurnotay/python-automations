variable "aws_profile" {
  type        = string
  description = "Enter local AWS profile used for deployment"
}

variable "aws_region" {
  type        = string
  description = "Enter the AWS region in which infrastructure is to be created"
}

variable "project_name" {
  type        = string
  description = "Enter a project name that will be used as a prefix to name resources"
}

variable "vpc_cidr" {
  type        = string
  description = "Enter the CIDR block of the VPC"
}

variable "pvt_sub_cidr" {
  type        = list(string)
  description = "Enter the list of CIDR blocks for the number of private subnets required in the VPC"
}

variable "pub_sub_cidr" {
  type        = list(string)
  description = "Enter the list of CIDR blocks for the number of public subnets required in the VPC"
}

variable "cont_def" {
  type = list(object({
    name  = string
    image = string
    cmd   = list(string)
    env   = map(string)
  }))
  description = "Enter the above values for container definitions"
}

variable "alert_email" {
  type        = string
  description = "Email address to receive SNS alerts for dirty file detections"
}