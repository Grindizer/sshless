provider "aws" {
  region = "eu-central-1"
}

##################################################################
# Data sources to get VPC, subnet, security group and AMI details
##################################################################
variable "vpc_id" {
  description = "VPC ID"
}


variable "user_data" {
  description = "ec2 user_data"
  default = <<EOF
#!/bin/bash
sudo start amazon-ssm-agent
EOF
}

data "aws_subnet_ids" "all" {
  vpc_id = "${var.vpc_id}"
}

data "aws_ami" "amazon_linux" {
  most_recent = true

  filter {
    name = "name"

    values = [
      "amzn-ami-hvm-*-x86_64-gp2",
    ]
  }

  filter {
    name = "owner-alias"

    values = [
      "amazon",
    ]
  }
}

module "security_group" {
  source = "terraform-aws-modules/security-group/aws"

  name        = "sshless-sg"
  description = "sshless-sg"
  vpc_id      = "${var.vpc_id}"

  ingress_cidr_blocks = ["0.0.0.0/0"]
  ingress_rules       = ["all-icmp"]
  egress_rules        = ["all-all"]
}

resource "aws_instance" "this" {
  count = 4
  ami                    = "${data.aws_ami.amazon_linux.id}"
  instance_type          = "t2.micro"
  subnet_id              = "${element(data.aws_subnet_ids.all.ids, 0)}"
  user_data              = "${var.user_data}"
  vpc_security_group_ids = ["${module.security_group.this_security_group_id}"]
  iam_instance_profile   = "${aws_iam_instance_profile.ec2_instance_profile.name}"
  tags = "${merge(
            map("Name", format("%s-%d", "web", count.index+1)),
            map("Owner", "demo"),
            map("Purpose", "sshless")
            )}"

}
