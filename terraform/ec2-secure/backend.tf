terraform {
  backend "s3" {
    bucket       = "harness-ai-bucket"
    key          = "dev/ec2-secure/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
