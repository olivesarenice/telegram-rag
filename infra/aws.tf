# S3 bucket for storing my files and providing downloadable hyperlinks
# During write to DB, also store the file in s3 prefix
# Pre-signed url gets generated during the query itself

# EC2 to run my docker instances

resource "aws_instance" "server" {
  ami                         = "ami-0a0e5d9c7acc336f1" # Ubuntu 22.04 LTS
  instance_type               = "t2.micro"
  key_name                    = "ec2-ssh-keypair"
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.ec2_profile.name # Tell EC2 to assume the role 

  vpc_security_group_ids = [
    aws_security_group.server_sg.id
  ]
  root_block_device {
    delete_on_termination = true
    volume_size           = 8
    volume_type           = "gp3"
  }
  tags = {
    Name = "telegram_rag"
  }

  depends_on = [aws_security_group.server_sg]
}

output "server" {
  value = aws_instance.server.public_ip
}
# Security Groups
resource "aws_security_group" "server_sg" {
  name        = "telegram_rag_server"
  description = "Managed by Terraform"
  vpc_id      = "vpc-02d1570808562a64c" # default

  // To Allow SSH Transport
  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      description = lookup(ingress.value, "description", null)
      from_port   = lookup(ingress.value, "from_port", null)
      to_port     = lookup(ingress.value, "to_port", null)
      protocol    = lookup(ingress.value, "protocol", null)
      cidr_blocks = lookup(ingress.value, "cidr_blocks", null)
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }


  tags = {
    Name = "telegram_rag"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# IAM for EC2

# EC2 needs to be able to assume a role
data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = [
      "sts:AssumeRole"
    ]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

# That grants it ECR permissions
data "aws_iam_policy_document" "ec2_ecr" {

  statement {
    actions = [
      "ecr:GetAuthorizationToken" # To login to the repo via docker login
    ]
    resources = ["*"]
  }

  statement {
    actions = [
      "ecr:GetDownloadUrlForLayer", # And download the image
      "ecr:BatchGetImage",
      "ecr:DescribeImages",
      "ecr:GetAuthorizationToken",
      "ecr:ListImages"
    ]
    resources = [aws_ecr_repository.repo.arn]
  }
}

resource "aws_iam_policy" "ec2_ecr" {
  name        = "telegram_rag_ec2_ecr"
  description = "Policy for EC2 to access ECR"
  policy      = data.aws_iam_policy_document.ec2_ecr.json
}

data "aws_iam_policy_document" "ec2_s3" {

  statement {
    actions = [
      "s3:PutObject",
      "s3:PutObjectAcl"
    ]
    resources = ["arn:aws:s3:::${aws_s3_bucket.public_tmp_bucket.bucket}/*"]
  }
}

resource "aws_iam_policy" "ec2_s3" {
  name        = "telegram_rag_ec2_s3"
  description = "Policy for EC2 to upload to S3"
  policy      = data.aws_iam_policy_document.ec2_s3.json
}

resource "aws_iam_role" "ec2_assume_role" {
  name               = "ec2_assume_role_telegram_rag"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
  lifecycle {
    create_before_destroy = true
  }
  force_detach_policies = true # Due to issue with dependency on instance-ptofile > role > policy https://github.com/hashicorp/terraform/issues/2761
  managed_policy_arns = [
    aws_iam_policy.ec2_ecr.arn,
    aws_iam_policy.ec2_s3.arn
  ]
}

# Automatically give the IAM role to EC2 once it starts up.
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "telegram_rag_ec2_profile"
  role = aws_iam_role.ec2_assume_role.name
}

# ECR

resource "aws_ecr_repository" "repo" {
  name                 = "telegram_rag"
  image_tag_mutability = "MUTABLE"
  encryption_configuration {
    encryption_type = "KMS"
  }
  tags = {
    Name = "telegram_rag"
  }
}

resource "aws_ecr_lifecycle_policy" "repo_policy" {
  repository = aws_ecr_repository.repo.name

  policy = <<EOF
  {
    "rules": [
      {
        "rulePriority": 1,
        "description": "Expire untagged images older than 3 days",
        "selection": {
          "tagStatus": "untagged",
          "countType": "sinceImagePushed",
          "countUnit": "days",
          "countNumber": 3
        },
        "action": {
          "type": "expire"
        }
      }
    ]
  }
  EOF
}

# S3 Bucket for hosting temp HTML files

# output "public_bucket_name" {
#   value     = 
#   sensitive = true # this is required if the sensitive function was used when loading .env file (more secure way)
# }

resource "aws_s3_bucket" "public_tmp_bucket" {
  bucket = local.envs["PUBLIC_S3_NAME"]
}

resource "aws_s3_bucket_acl" "public_tmp_bucket" {
  depends_on = [
    aws_s3_bucket_ownership_controls.public_tmp_bucket
  ]

  bucket = aws_s3_bucket.public_tmp_bucket.id
  acl    = "public-read"

}

resource "aws_s3_bucket_ownership_controls" "public_tmp_bucket" {
  bucket = aws_s3_bucket.public_tmp_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
  depends_on = [aws_s3_bucket_public_access_block.public_tmp_bucket]
}

resource "aws_s3_bucket_public_access_block" "public_tmp_bucket" {
  bucket = aws_s3_bucket.public_tmp_bucket.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "public_tmp_bucket" {
  bucket = aws_s3_bucket.public_tmp_bucket.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = "*",
        Action    = "s3:GetObject",
        Resource  = "arn:aws:s3:::${local.envs["PUBLIC_S3_NAME"]}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.public_tmp_bucket]
}

resource "aws_s3_bucket_lifecycle_configuration" "public_tmp_bucket" {
  bucket = aws_s3_bucket.public_tmp_bucket.id

  rule {
    status = "Enabled"
    id     = "expire-objects-after-1-day"
    expiration {
      days = 1
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }
  depends_on = [aws_s3_bucket_public_access_block.public_tmp_bucket]
}


