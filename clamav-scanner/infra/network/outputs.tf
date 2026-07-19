output "pvt_sub_ids" {
    value = aws_subnet.pvt_subs[*].id
}

output "vpc_id" {
  value = aws_vpc.vpc.id
}

output "scan_task_sg_id" {
  value = aws_security_group.scan_task_sg.id
}
