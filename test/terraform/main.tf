variable "region" {
  description = "aws region"
  default     = "eu-central-1"
}

provider "aws" {
  region = "${var.region}"
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


resource "aws_ssm_parameter" "example_parameter" {
  name  = "example.parameter"
  type  = "String"
  overwrite = true
  value = "I am an SSM parameter"
}


resource "aws_instance" "web" {
  count = 2
  ami                    = "${data.aws_ami.amazon_linux.id}"
  instance_type          = "t2.micro"
  subnet_id              = "${element(data.aws_subnet_ids.all.ids, 0)}"
  user_data              = "${var.user_data}"
  vpc_security_group_ids = ["${module.security_group.this_security_group_id}"]
  iam_instance_profile   = "${aws_iam_instance_profile.ec2_instance_profile.name}"
  tags = "${merge(
            map("Name", format("%s-%d", "web", count.index+1)),
            map("Owner", "demo"),
            map("Role", "web"),
            map("Purpose", "sshless")
            )}"

}

resource "aws_instance" "app" {
  count = 2
  ami                    = "${data.aws_ami.amazon_linux.id}"
  instance_type          = "t2.micro"
  subnet_id              = "${element(data.aws_subnet_ids.all.ids, 0)}"
  user_data              = "${var.user_data}"
  vpc_security_group_ids = ["${module.security_group.this_security_group_id}"]
  iam_instance_profile   = "${aws_iam_instance_profile.ec2_instance_profile.name}"
  tags = "${merge(
            map("Name", format("%s-%d", "app", count.index+1)),
            map("Owner", "demo"),
            map("Role", "app"),
            map("Purpose", "sshless")
            )}"

}



resource "aws_ssm_activation" "ssm_activation-1" {
  name               = "ssm_legacy-1"
  description        = "ssm_legacy-1"
  iam_role           = "${aws_iam_role.sshless-role-onprem.id}"
  registration_limit = "1"
  depends_on         = ["aws_iam_role_policy_attachment.ssm-policy-onprem"]
}

data "template_file" "user_data_onprem-1" {
  template = "${file("user_data.tpl")}"

  vars {
    region             = "${var.region}"
    activation_code    = "${aws_ssm_activation.ssm_activation-1.activation_code}"
    activation_id      = "${aws_ssm_activation.ssm_activation-1.id}"
  }
}

resource "aws_instance" "legacy-1" {
  count = 1
  ami                    = "${data.aws_ami.amazon_linux.id}"
  instance_type          = "t2.micro"
  subnet_id              = "${element(data.aws_subnet_ids.all.ids, 0)}"
  user_data              = "${data.template_file.user_data_onprem-1.rendered}"
  vpc_security_group_ids = ["${module.security_group.this_security_group_id}"]
  tags = "${merge(
            map("Name", "legacy-1"),
            map("Owner", "demo"),
            map("Role", "legacy"),
            map("Purpose", "sshless-onprem")
            )}"

}


resource "aws_ssm_activation" "ssm_activation-2" {
  name               = "ssm_legacy-2"
  description        = "ssm_legacy-2"
  iam_role           = "${aws_iam_role.sshless-role-onprem.id}"
  registration_limit = "1"
  depends_on         = ["aws_iam_role_policy_attachment.ssm-policy-onprem"]
}

data "template_file" "user_data_onprem-2" {
  template = "${file("user_data.tpl")}"

  vars {
    region             = "${var.region}"
    activation_code    = "${aws_ssm_activation.ssm_activation-2.activation_code}"
    activation_id      = "${aws_ssm_activation.ssm_activation-2.id}"
  }
}

resource "aws_instance" "legacy-2" {
  count = 1
  ami                    = "${data.aws_ami.amazon_linux.id}"
  instance_type          = "t2.micro"
  subnet_id              = "${element(data.aws_subnet_ids.all.ids, 0)}"
  user_data              = "${data.template_file.user_data_onprem-2.rendered}"
  vpc_security_group_ids = ["${module.security_group.this_security_group_id}"]
  tags = "${merge(
            map("Name", "legacy-2"),
            map("Owner", "demo"),
            map("Role", "legacy"),
            map("Purpose", "sshless-onprem")
            )}"

}
