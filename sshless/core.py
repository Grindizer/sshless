#!/usr/bin/env python

import sys
import logging
import base64
import boto3
import botocore


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
        self.ssm_max_results = 50
        self.credentials = {}
        try:
            self.ssm = self.get_client("ssm")
        except botocore.exceptions.ClientError as e:
            logger.critical(e)
            exit(1)

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

    def list_commands(self, CommandId=None, InstanceId=None):
        params = {
            'MaxResults': self.ssm_max_results
        }
        if CommandId:
            params['CommandId'] = CommandId
        if InstanceId:
            params['InstanceId'] = InstanceId

        response = self.ssm.list_commands(**params)
        commands = response['Commands']
        while True:
            if 'NextToken' not in response:
                break
            params['NextToken'] = response['NextToken']
            response = self.ssm.list_commands(**params)
        commands += response['Commands']
        return commands


    def list_command_invocations(self, CommandId=None, InstanceId=None, Details=False):
        params = {
            'MaxResults': self.ssm_max_results,
            'Details': Details
        }
        if CommandId:
            params['CommandId'] = CommandId
        if InstanceId:
            params['InstanceId'] = InstanceId

        response = self.ssm.list_command_invocations(**params)
        invocations = response['CommandInvocations']
        while True:
            if 'NextToken' not in response:
                break
            params['NextToken'] = response['NextToken']
            response = self.ssm.list_command_invocations(**params)
            invocations += response['CommandInvocations']
        return invocations

    def command_url(self, CommandId):
        if self.cfg["region"] is None:
            self.cfg["region"] = 'us-east-1'
        return 'https://console.aws.amazon.com/ec2/v2/home?region=' + \
            self.cfg["region"] + '#Commands:CommandId=' + \
            str(CommandId) + ';sort=CommandId'
  
