##
# The MIT License (MIT)
#
# Copyright (c) 2018 Megan Galloway
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
##

import json
import os
import pprint
import sys
import tarfile
from datetime import datetime, timezone
from time import sleep

import pfucking_shell_scripts.boto_monkey  # this import is required for binary packaging to work
import boto3
import click
import sh
from sh import scp, ssh

from pfucking_shell_scripts.pfss_const import REQUIRED_CONFIGS, TAR_FILENAME, SCRIPTS_DIR
from pfucking_shell_scripts.pfss_util import log_prefix_factory, load_server_config, default_datetime

today_string = '{0:%Y-%m-%d}'.format(datetime.now(timezone.utc))

log_prefix = log_prefix_factory('pfss')

ec2client = boto3.client('ec2')


@click.command()
@click.argument('server')
def pfss(server: str):
    click.echo('{} Running pfss for {}'.format(log_prefix(), server))

    config = load_config(server)
    click.echo('{} Using config\n{}'.format(log_prefix(), pprint.pformat(config, indent=2)))

    validate_config(config)  # exits if we don't have enough info to continue

    instance_id = create_instance(config)

    tag_instance(config, instance_id)

    wait_for_instance_boot(instance_id)

    public_dns = wait_for_public_dns(instance_id)

    # just build this once
    # username@whatever-123-abc.cloudprovider.com
    destination = config['username'] + '@' + public_dns

    wait_for_ssh(config, destination)

    send_scripts_to_server(config, destination, TAR_FILENAME, SCRIPTS_DIR)

    run_scripts(config, destination)

    clean_up_tars(config, destination, TAR_FILENAME)

    click.echo('{} All done! Check out your instance {} with DNS {}'.format(log_prefix(), instance_id, public_dns))


def create_instance(config: dict) -> str:

    ec2 = boto3.resource('ec2')

    create_instance_args = {
        'ImageId': config['image'],
        'InstanceType': config['size'],
        'KeyName': config['key_name'],
        'MinCount': 1,
        'MaxCount': 1,
    }

    if 'availability_zone' in config:
        placement_arg = dict()
        placement_arg['AvailabilityZone'] = config['availability_zone']
        create_instance_args['Placement'] = placement_arg
    if 'security_groups' in config:
        sg = config['security_groups']
        if type(sg) is not list:
            sg = [sg]
        create_instance_args['SecurityGroupIds'] = sg

    create_instance_args['DryRun'] = False
    instances = ec2.create_instances(**create_instance_args)  # returns [ec2.Instance('id')]

    instance = instances[0]
    click.echo('{} Launched instance with ID {}'.format(log_prefix(), instance.instance_id))

    return instance.instance_id


def tag_instance(config, instance_id):
    name_tag = config['name'] + '-' + today_string
    click.echo('{} Tagging instance as {}'.format(log_prefix(), name_tag))

    response = ec2client.create_tags(
        Resources=[
            instance_id,
        ],
        Tags=[
            {
                'Key': 'Name',
                'Value': name_tag
            },
        ]
    )


def wait_for_instance_boot(instance_id: str) -> str:

    # poll for the state
    describe_instances_args = {
        "InstanceIds" : [instance_id]
    }

    response = ec2client.describe_instances(**describe_instances_args)
    click.echo('{}\n{}'.format(log_prefix(), json.dumps(response, indent=4, sort_keys=True, default=default_datetime)))

    current_state = response['Reservations'][0]['Instances'][0]['State']['Name']

    tries = 10
    while current_state != 'running' and tries >= 1:
        if current_state == 'pending':
            click.echo('{} Instance is still pending, waiting a minute with {} tries left'.format(log_prefix(), tries))
            sleep(60)
            response = ec2client.describe_instances(**describe_instances_args)
            current_state = response['Reservations'][0]['Instances'][0]['State']['Name']
            tries -= 1
        else:
            click.echo('{} Instance {} is in state {}, abandoning ship. Manual cleanup probably required'.format(log_prefix(), instance_id, current_state))
            sys.exit(1)


def wait_for_public_dns(instance_id: str) -> str:

    describe_instances_args = {
        "InstanceIds" : [instance_id]
    }

    # poll until the public dns is in the response
    response = ec2client.describe_instances(**describe_instances_args)

    public_dns = response['Reservations'][0]['Instances'][0]['PublicDnsName']
    click.echo('{}\n{}'.format(log_prefix(), json.dumps(response, indent=4, sort_keys=True, default=default_datetime)))

    tries = 10
    while not public_dns and tries >= 1:
        click.echo('{} Instance is running, waiting for public DNS with {} tries left'.format(log_prefix(), tries))
        sleep(60)
        response = ec2client.describe_instances(**describe_instances_args)
        public_dns = response['Reservations'][0]['Instances'][0]['PublicDnsName']
        tries -= 1

    if not public_dns:
        click.echo('{} Unable to get public DNS info for instance {} , abandoning ship. Manual cleanup probably required'.format(log_prefix(), instance_id))
        sys.exit(1)

    return public_dns


def wait_for_ssh(config: dict, destination:str):
    """
      Just attempt to connect with ssh until it succeeds.
      Inspect the error. If we see "Connection closed by remote host" it means the box isn't up yet. Try again.
      If we see a different error, explode
    """
    tries = 10
    for i in range(tries):
        click.echo('{} Waiting for ssh access with {} tries left'.format(log_prefix(), tries - i))

        try:
            # ssh -i ~/keys/hello.key username@whatever-123-abc.cloudprovider.com echo 'Ready!'
            ssh('-i', config['private_key_path'], destination, 'echo', 'Ready!')
            break
        except sh.ErrorReturnCode_1 as e1:
            if str(e1).find('Connection closed') == -1:
                raise(e1)
        except sh.ErrorReturnCode_255 as e255:
            if str(e255).find('Connection timed out') == -1:
                raise(e255)
        sleep(60)


def load_config(server: str) -> dict:
    default_config = load_server_config('defaults')
    whatever_config = load_server_config(server)

    default_config.update(whatever_config)  # overlay specific config on top of defaults and return it

    return default_config


def validate_config(config: dict):
    errors = ''
    for c in REQUIRED_CONFIGS:
        if not config.get(c):
            errors += '\nMissing config: {}'.format(c)

    # check if any scripts are missing or not executable
    for script_path in config.get(SCRIPTS_DIR):
        if not os.access(os.path.join(script_path), os.X_OK):
            errors += '\nScript is not executable: {} '.format(script_path)

    if errors:
        click.echo('{} HEY ERRORS: {}'.format(log_prefix(), errors))
        sys.exit(1)


def send_scripts_to_server(config: dict, destination: str, tar_filename: str, scripts_dir: str):
    click.echo('{} Creating tar of local scripts'.format(log_prefix()))
    with tarfile.open(tar_filename, "w:gz") as tar:
        for script_path in config['scripts']:
            tar.add(script_path)
        tar.list(verbose=True)

    click.echo('{} Sending scripts to instance'.format(log_prefix()))
    destination_with_location = destination + ':.'
    # scp -i ~/keys/hello.key local_scripts.tar.gz username@whatever-123-abc.cloudprovider.com:.
    scp('-i', config['private_key_path'], tar_filename, destination_with_location)

    click.echo('{} Extracting tar on instance'.format(log_prefix()))
    # ssh -i ~/keys/hello.key username@whatever-123-abc.cloudprovider.com tar xzf local_scripts.tar.gz
    ssh('-i', config['private_key_path'], destination, 'tar', 'xzf', tar_filename)


def run_scripts(config: dict, destination: str):
    # run everything we copied over, not everything that might already be there
    for script_path in config['scripts']:
        click.echo('{} Running {}'.format(log_prefix(), script_path))
        ssh('-i', config['private_key_path'], destination, script_path)


def clean_up_tars(config: dict, destination: str, tar_filename: str):
    click.echo('{} Deleting local and remote tar files'.format(log_prefix()))

    # ssh -i ~/keys/hello.key username@whatever-123-abc.cloudprovider.com rm local_scripts.tar.gz
    ssh('-i', config['private_key_path'], destination, 'rm', tar_filename)

    os.remove(tar_filename)


if __name__ == '__main__':

    pfss()