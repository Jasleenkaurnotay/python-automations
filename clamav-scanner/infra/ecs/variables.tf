variable "aws_region" {
    type = string
    description = "Enter the AWS region in which infrastructure is to be created"
}

variable "project_name" {
    type = string
    description = "Enter a project name that will be used as a prefix to name resources"
}

variable "tags" {
    type = map(string)
    description = "Tags declared as local variable in root module"
}

variable "cont_def_map" {
    type = map(object({
        name = string
        image = string
        cmd = list(string)
        env = map(string)
    }))
    description = "Container definition input"
}