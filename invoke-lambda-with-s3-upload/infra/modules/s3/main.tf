# Receive CSV uploads
# Notify lambda when the object arrives

# Create S3 bucket
resource "aws_s3_bucket" "data_bucket" {
    bucket = "${var.project_name}-data-bucket"
    tags = {
        Name = "${var.project_name}-data-bucket"
        ManagedBy = "Terraform"
    }
}

