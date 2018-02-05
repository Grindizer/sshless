====================
SSHLess with AWS SSM
====================

.. image:: https://circleci.com/gh/giuliocalzolari/sshless.png?style=shield
    :target: https://circleci.com/gh/giuliocalzolari/sshless/tree/master

.. image:: https://badge.fury.io/py/sshless.svg
    :target: https://badge.fury.io/py/sshless

Config
------

this script is designed to run across multiple accounts and across multiple regions you can switch between regions/accounts using some OS vars

To execute an assume role action
::

  $ export AWS_SSM_ROLE=arn:aws:iam::111111111:role/admin


Cache Filters
-------------

sshless use a local file to save the Target filters in order to simplify and avoid to have long command line history

Example::

  $ sshless cmd --name web-001 "uname -a"
  ..... output omitted ....
  $ cat ~/.sshless/filters     # local file with your filter
    {
    "Targets": [{
        "Key": "tag:Name",
        "Values": ["web-001"]
      }]
    }
  $ sshless cmd "uname -a"   # valid command to the same target
  ..... output omitted ....


Command
-------

Instance ID Filter::

  $ export SSHLESS_ID_FILTER=i-0da73e7c56e628889,i-0b83e0b9f8f900500
  $ sshless cmd "uname -a"

  $ sshless cmd  -i i-0da73e7c56e628889,i-0b83e0b9f8f900500 "uname -a"

Tag Name Filter::

  $ export SSHLESS_NAME_FILTER=web-001
  $ sshless cmd "uname -a"
  $ sshless cmd  --name web-001 "uname -a"

Advanced Tag filter::

  $ export SSHLESS_FILTER=tag:Environment=DEV
  $ sshless cmd "uname -a"
  $ sshless cmd  --filters tag:Environment=DEV "uname -a"

SSM Parameter store integration::

  $ sshless cmd  --name web-001 "echo {{ssm:db.host}}"

List of all SSM instances Online::

  $ sshless list
  $ sshless list --show-tags


Execute command and save output to S3::

  $ sshless cmd  --name web-001 "uname -a" --s3-output=[your-s3-bucket-ssm-output]
  $ sshless cmd  --name web-001 "uname -a" --s3-output=[your-s3-bucket-ssm-output] --preserve-s3-output




License
-------------

sshless is licensed under the `MIT <LICENSE>`_.
