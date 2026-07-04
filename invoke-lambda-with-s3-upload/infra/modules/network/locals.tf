locals {
    pvt_sub_map = {
        for idx, sub in var.pvt_subnet_data : sub.cidr => {
            cidr = sub.cidr
            name = sub.name
            az = data.aws_availability_zones.azs.names[idx]
        }
    }
}