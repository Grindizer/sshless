=======
SSHLess with AWS SSM
=======

Config
-----

this script is designed to run across multiple accounts and across multiple regions you can switch between regions/accounts using some OS vars

To execute an assume role action::

  $ export AWS_SSM_ROLE=arn:aws:iam::111111111:role/admin


Command
-----
::

  $ sshless cmd  -i i-0b83e0b9f8f900500 "uname -a"
  $ sshless cmd  --filter tag:Environment=DEV "uname -a"
  $ sshless cmd  --name web-001 "uname -a"


  $ sshless info --show-tags



License
-------------

sshless is licensed under the `MIT <LICENSE>`_.
