resource "aws_vpc" "vpc" {
    cidr_block = var.vpc_cidr
    enable_dns_support = true
    enable_dns_hostnames = true
    tags = {
        Name = "${var.project_name}-${var.vpc_name}"
        Managed_By = "Terraform"
    }
}

# Query availability zones in the region
data "aws_availability_zones" "azs" {
    state = "available"
}

# Create private subnets
resource "aws_subnet" "pvt_subnet" {
    # 1. loop through the local map 
    for_each = local.pvt_sub_map
    vpc_id = aws_vpc.vpc.id

    # 2. Reference the current item's data from the map
    cidr_block = each.value.cidr       # we just need the map's key here
    availability_zone = each.value.az
    tags = {
        Name = "${var.project_name}-${each.value.name}"
        Managed_By = "Terraform"
    }
}

# Create private route table for the private subnets
resource "aws_route_table" "pvt-rt" {
    vpc_id = aws_vpc.vpc.id
    # No route block needed since we dont have a NAT. Also, route for S3 g/w endpoint gets automatically added
}

# Associate private subnets with route table
resource "aws_route_table_association" "pvt-rt-assoc" {
    for_each = local.pvt_sub_map
    subnet_id = aws_subnet.pvt_subnet[each.key].id
    route_table_id = aws_route_table.pvt-rt.id
}


# Create VPC endpoint - S3 Gateway endpoint type
resource "aws_vpc_endpoint" "s3_gw_ep" {
    vpc_id = aws_vpc.vpc.id
    service_name = "com.amazonaws.${var.aws_region}.s3"
    vpc_endpoint_type = "Gateway"

    # Map route table here
    route_table_ids = [aws_route_table.pvt-rt.id]
    tags = {
        Name = "${var.project_name}-s3-gw-endpoint"
        Managed_By = "Terraform"
    }
}







