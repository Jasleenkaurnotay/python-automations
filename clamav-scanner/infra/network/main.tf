# Query availability zones for the VPC
data "aws_availability_zones" "avail_azs" {
    state = "available"
}

# Create VPC resource
resource "aws_vpc" "vpc" {
    cidr_block = var.vpc_cidr
    enable_dns_hostnames = true
    enable_dns_support = true
    tags = merge({ Name = "${var.project_name}-vpc"}, var.tags)
}

# Create private subnets
resource "aws_subnet" "pvt_subs" {
    count = length(var.pvt_sub_cidr)
    vpc_id = aws_vpc.vpc.id
    cidr_block = var.pvt_sub_cidr[count.index]
    availability_zone = data.aws_availability_zones.avail_azs.names[count.index]
    tags = merge({ Name = "${var.project_name}-${count.index}-pvt-sub"}, var.tags)
}

# Create public subnets
resource "aws_subnet" "pub_subs" {
    count = length(var.pub_sub_cidr)
    vpc_id = aws_vpc.vpc.id
    cidr_block = var.pub_sub_cidr[count.index]
    availability_zone = data.aws_availability_zones.avail_azs.names[count.index]
    tags = merge({ Name = "${var.project_name}-${count.index}-pub-sub"}, var.tags)
}

# Create igw
resource "aws_internet_gateway" "igw" {
    vpc_id = aws_vpc.vpc.id
    tags = merge({ Name = "${var.project_name}-igw"}, var.tags)
}

# Create public route table for igw and NAT
resource "aws_route_table" "pub_rt" {
    vpc_id = aws_vpc.vpc.id

    route {
        cidr_block = "0.0.0.0/0"
        gateway_id = aws_internet_gateway.igw.id
    }
}

# Associate the public route table with the public subnets
resource "aws_route_table_association" "pub_rt_assoc" {
    count = length(var.pub_sub_cidr)
    subnet_id = aws_subnet.pub_subs[count.index].id
    route_table_id = aws_route_table.pub_rt.id   
}

# Allocate EIP for NAT gateway
resource "aws_eip" "eip" {
    domain = "vpc"
    depends_on = [ aws_internet_gateway.igw ]
    tags = merge({ Name = "${var.project_name}-eip"}, var.tags)
}

# Create NAT gateway
resource "aws_nat_gateway" "nat_gw" {
    allocation_id = aws_eip.eip.id
    subnet_id = aws_subnet.pub_subs[0].id
    depends_on = [ aws_internet_gateway.igw ]
    tags = merge({ Name = "${var.project_name}-nat-gw"}, var.tags)
}

# Create private route table for igw and NAT
resource "aws_route_table" "pvt_rt" {
    vpc_id = aws_vpc.vpc.id

    route {
        cidr_block = "0.0.0.0/0"
        nat_gateway_id = aws_nat_gateway.nat_gw.id
    }
}

# Associate the private route table with the public subnets
resource "aws_route_table_association" "pvt_rt_assoc" {
    count = length(var.pvt_sub_cidr)
    subnet_id = aws_subnet.pvt_subs[count.index].id
    route_table_id = aws_route_table.pvt_rt.id   
}

#### Security group of Scan task
resource "aws_security_group" "scan_task_sg" {
  name        = "${var.project_name}-scan-task-sg"
  description = "Security group for ClamAV scan ECS task"
  vpc_id      = aws_vpc.vpc.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge({ Name = "${var.project_name}-scan-task-sg" }, var.tags)
}
