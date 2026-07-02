output "vpc_id" {
    value = aws_vpc.vpc.id
}

output "pvt_sub_ids" {
    value = values(aws_subnet.pvt_subnet)[*].id
}