variable "project_name" {
    type = string
    description = "Enter a project name that will be used as a prefix to name resources"
}

variable "tags" {
    type = map(string)
    description = "Tags declared as local variable in root module"
}

variable "alert_email" {
    type        = string
    description = "Email address to receive SNS alerts for dirty file detections"
}