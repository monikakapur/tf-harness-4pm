output "instance_id" {
  value = aws_instance.demo.id
}

output "private_ip" {
  value = aws_instance.demo.private_ip
}

output "security_group_id" {
  value = aws_security_group.demo_sg.id
}
