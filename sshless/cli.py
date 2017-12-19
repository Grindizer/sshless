#!/usr/bin/env python

import sys
import logging
import time
import json
from datetime import date, datetime
import os
from functools import wraps
import click
from core import SSHLess
from shell import SSHLessCmd
from termcolor import colored


lpad = 13
lfill = '%13s'

# Setup simple logging for INFO
logging.getLogger("botocore").setLevel(logging.CRITICAL)
logger = logging.getLogger("sshless")
handler = logging.StreamHandler(sys.stdout)
FORMAT = "[%(asctime)s][%(levelname)s] %(message)s"
handler.setFormatter(logging.Formatter(FORMAT))
logger.addHandler(handler)
logger.setLevel(logging.INFO)



def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

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
def cli(ctx, iam, region):  # pragma: no cover
    ctx.obj = {
        "options": {},
        "region": region,
        "iam": iam
    }
    pass







@cli.command()
@click.option('-f', '--filters', default="PingStatus=Online", help='advanced Filter default: PingStatus=Online')
@click.option('-t', '--show-tags', is_flag=True, default=False)
@click.pass_context
def info(ctx, filters, show_tags):
    """ssm.describe_instance_information """

    sshless = SSHLess(ctx.obj)
    fl = []
    for ff in filters.split(","):
        key, val = ff.split("=")
        fl.append({"Key": key, "Values": [val] })

    response = sshless.ssm.describe_instance_information(
        Filters=fl
    )

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

    click.echo(json.dumps(full_info, indent=2, default=json_serial))

@cli.command()
@click.argument('command')
@click.option('-s', '--show-stats', is_flag=True, default=False)
@click.option('-n', '--name', default=None, help='Filter based on tag:Name')
@click.option('-f', '--filters', default=None, help='advanced Filter')
@click.option('-i', '--instances', default=None, help='instances ID')
@click.option('--maxconcurrency', default=None, help='MaxConcurrency')
@click.option('--maxerrors', default=1, help='MaxErrors')
@click.option('--comment', default='sshless cli', help='Command invocation comment')
@click.option('--interval', default=1, help='Check interval (default: 1.0s)')
@click.pass_context
def cmd(ctx, command, show_stats, name, filters, instances, maxconcurrency, maxerrors,  comment, interval):
    """Send SSM AWS-RunShellScript to target, quick emulation of virtual SSH interface"""

    sshless = SSHLess(ctx.obj)

    if name and filters:
        click.echo("[{}] name and filters are mutually exclusive".format(colored("Error", "red")))
        sys.exit(1)

    fl = []

    params = {
        "DocumentName": "AWS-RunShellScript",
        "Parameters": {"commands": [command]},
        "Comment": comment,
        "MaxErrors": str(maxerrors)
    }

    if instances:
        if name or filters:
            click.echo("[{}] instances filters override tag or advanced filter".format(colored("Warn", "yellow")))
        params["InstanceIds"] = instances.split(",")

    elif name:
        fl.append({'Key': 'tag:Name','Values': [name] })
        params["Targets"] = fl
    elif filters:
        for ff in filters.split(","):
            key, val = ff.split("=")
            fl.append({"Key": key, "Values": [val] })
        params["Targets"] = fl


    if maxconcurrency:
        params["MaxConcurrency"] = str(maxconcurrency)

    cmd = sshless.ssm.send_command(**params)['Command']

    #click.echo('==> ' + ssm.command_url(cmd['CommandId']))

    while True:
        time.sleep(interval)
        out = sshless.list_commands(CommandId=cmd['CommandId'])[0]
        if out["TargetCount"] == 0:
            click.echo(colored("TargetCount: 0 ", "red"))
            break
        # Print final results when done
        # click.echo(json.dumps(out, indent=2, default=json_serial))


        if out['Status'] not in ['Pending', 'InProgress']:
            if out['TargetCount'] == out['CompletedCount']:
                if show_stats:
                    command_stats(out)

                res = sshless.list_command_invocations(
                    cmd['CommandId'], Details=True)
                if len(res) != 0:
                    click.echo()
                    for i in res:
                        click.echo("[{}] {} {}".format(get_status(i['Status']), i['InstanceId'], i['InstanceName']))
                        for cp in i['CommandPlugins']:
                            click.echo(cp['Output'])
                break



def command_stats(i, invocation_url=None):
    """Print results from ssm.list_commands()"""
    if invocation_url:
        click.echo('==> ' + invocation_url)

    click.echo(lfill % ('[' + get_status(i['Status']) + '] ') + i['CommandId'])
    click.echo(' ' * lpad + 'Requested: '.ljust(lpad) +
               str(i['RequestedDateTime'].replace(microsecond=0)))
    click.echo(' ' * lpad + 'Command: '.ljust(lpad) + i['Parameters']["commands"][0])
    if len(i['InstanceIds']) > 0:
        click.echo(' ' * lpad + 'InstanceIds: '.ljust(lpad) +
                   str(','.join(i['InstanceIds'])))
    if len(i['Targets']) > 0:
        click.echo(' ' * lpad + 'Target: '.ljust(lpad) +
                   i['Targets'][0]['Key'] + ' - ' + i['Targets'][0]['Values'][0])
    click.echo(' ' * lpad + 'Stats: '.ljust(lpad) + 'Targets: ' + str(i['TargetCount']) +
               ' Completed: ' + str(i['CompletedCount']) +
               ' Errors: ' + str(i['ErrorCount']))



def get_status(status):
   if status == "Success":
       return colored(status, "green")
   else:
       return colored(status, "red")



if __name__ == '__main__':
    cli()
