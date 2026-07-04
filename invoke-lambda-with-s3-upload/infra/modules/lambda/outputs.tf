output "lambda_func_arn" {
    value = aws_lambda_function.lambda_func.arn
}

output "lambda_sg_id" {
    value = aws_security_group.lambda_sg.id
}