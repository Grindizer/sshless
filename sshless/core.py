#!/usr/bin/env python

import sys
import logging
import base64
import boto3
import botocore
from util import get_status, format_json

logger = logging.getLogger("sshless")


class SSHLess(object):
    """Summary

    Attributes:
        cfg (dict): Config with all related parameters
        ssm (boto3.client): SSM boto3.client
        target (list): SSM target
    """

    def __init__(self, cfg):
        """Init class

        Args:
            args (object): CFG
        """
        self.cfg = cfg
        self.credentials = {}
        self.ssm = self.get_client("ssm")


    def get_client(self, service):
        """boto3.client helper
        can return a simple boto3.client or execute an sts assume_role action

        Args:
            service (string): AWS service

        Returns:
            boto3.client: client to execute action into a specific account and region
        """
        if self.cfg["iam"] == "":
            return boto3.client(service, region_name=self.cfg["region"])

        if self.credentials == {}:
            logger.info("assume Role: {}".format(self.cfg["iam"]))
            sts_client = boto3.client("sts")
            self.credentials = sts_client.assume_role(
                RoleArn=self.cfg["iam"],
                RoleSessionName="sshless")["Credentials"]

        return boto3.client(
            service,
            region_name=self.cfg["region"],
            aws_access_key_id=self.credentials["AccessKeyId"],
            aws_secret_access_key=self.credentials["SecretAccessKey"],
            aws_session_token=self.credentials["SessionToken"])

    def send_command(self, params):
        """send_command
        ssm send_command
        http://boto3.readthedocs.io/en/latest/reference/services/ssm.html#SSM.Client.send_command

        Args:
            params (object): SSM send_command object
        """
        logger.info("Send command")
        logger.debug(format_json(params))
        return self.ssm.send_command(**params)



    def list_commands(self, CommandId=None):
        """list_commands
        ssm list_commands
        http://boto3.readthedocs.io/en/latest/reference/services/ssm.html#SSM.Client.list_commands

        Args:
            CommandId (string): SSM CommandId
        """

        params = {
            "CommandId": CommandId
        }

        command = self.ssm.list_commands(**params)['Commands']
        logger.debug(command)
        return command

    def list_command_invocations(self, CommandId=None):
        """list_command_invocations
        ssm list_command_invocations
        http://boto3.readthedocs.io/en/latest/reference/services/ssm.html#SSM.Client.list_command_invocations

        Args:
            CommandId (string): SSM CommandId
        """
        params = {
            'Details': True,
            "CommandId": CommandId
        }
        invocation = self.ssm.list_command_invocations(**params)['CommandInvocations']
        logger.debug(invocation)
        return invocation


    def command_url(self, CommandId):
        if self.cfg["region"] is None:
            self.cfg["region"] = 'us-east-1'
        return 'https://console.aws.amazon.com/ec2/v2/home?region=' + \
            self.cfg["region"] + '#Commands:CommandId=' + \
            str(CommandId) + ';sort=CommandId'

    def delete_s3_output(self, key, s3_output):
        logger.debug("deleting s3 : {}".format(key))
        s3 = self.get_client("s3")
        s3.delete_object(
            Bucket=s3_output,
            Key=key
        )

    def get_s3_output(self, cmd_id, s3_output):
        s3 = self.get_client("s3")

        # Create a paginator to pull 1000 objects at a time
        paginator = s3.get_paginator('list_objects')
        operation_parameters = {'Bucket': s3_output,
                                'Prefix': '{}/'.format(cmd_id)}
        pageresponse = paginator.paginate(**operation_parameters)
        logger.info("List s3 output")
        logger.debug(operation_parameters)
        # PageResponse Holds 1000 objects at a time and will continue to repeat in chunks of 1000.
        for pageobject in pageresponse:
            if len(pageobject["Contents"]) > 1:
                logger.warn("more than one file found")
                logger.info(operation_parameters)
                logger.debug(pageobject["Contents"])

            for obj in pageobject["Contents"]:

                if obj["Key"].endswith("stdout"):
                    status = "Success"
                elif obj["Key"].endswith("stderr"):
                    status = "Error"
                else:
                    logger.warn("Unknown s3 obejct: {}".format(obj["Key"]))
                    continue

                output = obj["Key"].split("/")
                # GET s3 output
                objout = s3.get_object(Bucket=s3_output, Key=obj["Key"])

                return status, output[1], obj["Key"], objout['Body'].read().decode('utf-8')
