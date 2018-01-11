#!/usr/bin/env python

import sys
import logging
import time
import os
from functools import wraps
import click
import boto3
from core import SSHLess
from util import get_status, format_json
from termcolor import colored



# Setup simple logging for INFO
logging.getLogger("botocore").setLevel(logging.CRITICAL)
logger = logging.getLogger("sshless")
handler = logging.StreamHandler(sys.stdout)
FORMAT = "[%(asctime)s][%(levelname)s] %(message)s"
handler.setFormatter(logging.Formatter(FORMAT))
logger.addHandler(handler)
logger.setLevel(logging.WARN)




def catch_exceptions(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        """
        Invokes ``func``, catches expected errors, prints the error message and
        exits sceptre with a non-zero exit code.
        """
        try:
            return func(*args, **kwargs)
        except:
            logger.error(sys.exc_info()[1])
            sys.exit(1)

    return decorated


@click.group()
@click.version_option(prog_name="sshless")
@click.pass_context
@click.option(
    "--iam", default=os.environ.get("AWS_SSM_ROLE", ""), help="IAM to assume")
@click.option(
    "--region",
    default=os.environ.get("AWS_DEFAULT_REGION", "eu-west-1"),
    help="AWS region")
@click.option('-v', '--verbose', is_flag=True, multiple=True)
def cli(ctx, iam, region, verbose):
    ctx.obj = {
        "options": {},
        "region": region,
        "iam": iam,
        "verbosity": len(verbose)
    }

    if ctx.obj["verbosity"] == 1:
        logger.setLevel(logging.INFO)
    elif ctx.obj["verbosity"] > 1:
        logger.setLevel(logging.DEBUG)
        logger.debug("log level is set to DEBUG")
    pass




@cli.command()
@click.option('-f', '--filters', default="PingStatus=Online", help='advanced Filter default: PingStatus=Online')
@click.option('-t', '--show-tags', is_flag=True, default=False)
@click.pass_context
def list(ctx, filters, show_tags):
    """ssm.describe_instance_information """

    sshless = SSHLess(ctx.obj)
    fl = []
    for ff in filters.split(","):
        key, val = ff.split("=")
        fl.append({"Key": key, "Values": [val] })

    try:
        response = sshless.ssm.describe_instance_information(
            Filters=fl
        )
    except:
        click.echo("[{}] {}".format(colored("ERROR", "red"), sys.exc_info()[1] ))
        sys.exit(1)


    if show_tags:
        ids = []
        infos = {}
        # ADD EC2 tags
        for i in response["InstanceInformationList"]:
            ids.append(i["InstanceId"])

        ec2 = sshless.get_client("ec2")
        tags = ec2.describe_tags(
            Filters=[{'Name': 'resource-id',
                    'Values': ids}]
        )["Tags"]
        for tag in tags:
            if tag["ResourceId"] not in infos.keys():
                infos[tag["ResourceId"]] = []
            infos[tag["ResourceId"]].append({tag.get("Key", ""): tag.get("Value", "")})

        full_info = []
        for inst in response["InstanceInformationList"]:
            inst["Tags"] = infos.get(inst["InstanceId"], {})
            full_info.append(inst)

    else:
        full_info = response["InstanceInformationList"]

    click.echo(format_json(full_info))

@cli.command()
@click.argument('command')
@click.option('-s', '--show-stats', is_flag=True, default=False)
@click.option('-n', '--name', default=os.environ.get("SSHLESS_NAME_FILTER", None), help='Filter based on tag:Name')
@click.option('-f', '--filters', default=os.environ.get("SSHLESS_FILTER", None), help='advanced Filter')
@click.option('-i', '--instances', default=os.environ.get("SSHLESS_ID_FILTER", None), help='instances ID')
@click.option('--maxconcurrency', default=None, help='Max concurrency allowed (Optional)')
@click.option('--maxerrors', default=1, help='Max errors allowed (default: 1)')
@click.option('--comment', default='sshless cli', help='Command invocation comment')
@click.option('--interval', default=1, help='Check interval (default: 1.0s)')
@click.option('--timeout', default=600, help='TimeoutSeconds - If this time is reached and the command has not already started executing, it will not execute.')
@click.option('--s3-output', default=os.environ.get("SSHLESS_S3_OUTPUT", None), help='S3 output (Optional)')
@click.option('--preserve-s3-output', is_flag=True, default=False, help='Preserve S3 output (Optional)')
@click.pass_context
@catch_exceptions
def cmd(ctx, command, show_stats, name, filters, instances, maxconcurrency, maxerrors,  comment, interval, timeout, s3_output, preserve_s3_output):
    """SSM AWS-RunShellScript emulation SSH interface"""

    sshless = SSHLess(ctx.obj)
    if name and filters:
        click.echo("[{}] name and filters are mutually exclusive".format(colored("Error", "red")))
        sys.exit(1)

    fl = []
    params = {
        "DocumentName": "AWS-RunShellScript",
        "Parameters": {"commands": [command]},
        "Comment": comment,
        "MaxErrors": str(maxerrors),
        "TimeoutSeconds": int(timeout)
    }

    if instances:
        if name or filters:
            click.echo("[{}] instances filters override tag or advanced filter".format(colored("Warn", "yellow")))
        params["InstanceIds"] = instances.split(",")
        target = "InstanceIds: {}".format(instances)

    elif name:
        if filters:
            click.echo("[{}] name filter override advanced filter".format(colored("Warn", "yellow")))

        fl.append({'Key': 'tag:Name','Values': [name] })
        params["Targets"] = fl
        target = "Tag Name Filter: tag:Name={}".format(name)
    elif filters:
        for ff in filters.split(","):
            key, val = ff.split("=")
            fl.append({"Key": key, "Values": [val] })
        params["Targets"] = fl
        target = "Tag Filter: {}".format(filters)

    if maxconcurrency:
        params["MaxConcurrency"] = str(maxconcurrency)

    if s3_output:
        params["OutputS3BucketName"] = s3_output

    cmd_id = sshless.send_command(params)['Command']['CommandId']

    while True:
        time.sleep(interval)
        out = sshless.list_commands(CommandId=cmd_id)[0]
        if out["TargetCount"] == 0:
            click.echo(colored("TargetCount: 0", "red"))
            break

        if out['Status'] not in ['Pending', 'InProgress']:
            if out['TargetCount'] == out['CompletedCount']:

                logger.debug(sshless.command_url(cmd_id))
                logger.debug(format_json(out))

                if show_stats:
                    print_stats(out, target)

                res = sshless.list_command_invocations(cmd_id)
                if len(res) != 0:
                    if s3_output:
                        status, instanceid, key, body = sshless.get_s3_output(cmd_id, s3_output)
                        click.echo("[{}] {}".format(get_status(status), instanceid))
                        click.echo(body)
                        if preserve_s3_output == False:
                            sshless.delete_s3_output(key, s3_output)

                    else:
                        for i in res:
                            click.echo("[{}] {} {}".format(get_status(i['Status']), i['InstanceId'], i['InstanceName']))
                            for cp in i['CommandPlugins']:
                                click.echo(cp['Output'])
                break



def print_stats(i,target):

    output = """[{}]
 CommandId: {}
 Requested: {}
 Command: {}
 {}
 Stats: Targets: {}  Completed: {}  Errors: {}
    """.format(get_status(i['Status']),
    i['CommandId'],
    i['RequestedDateTime'].replace(microsecond=0),
    i['Parameters']["commands"][0],
    target,
    i['TargetCount'],
    i['CompletedCount'],
    i['ErrorCount']
    )
    click.echo(output)







if __name__ == '__main__':
    cli()
