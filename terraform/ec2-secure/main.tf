data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_security_group" "demo_sg" {
  name        = "${var.project_name}-sg"
  description = "Security group for Harness Ollama Terraform demo"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH allowed only from my public IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_cidr]
  }

  egress {
    description = "Allow HTTPS outbound only"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-sg"
    Environment = "dev"
  }
}

resource "aws_instance" "demo" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = "t3.micro"
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.demo_sg.id]

  monitoring = true

  metadata_options {
    http_tokens = "required"
  }

  root_block_device {
    volume_size = 8
    encrypted   = true
  }

  tags = {
    Name        = "${var.project_name}-ec2"
    Environment = "dev"
  }
}
