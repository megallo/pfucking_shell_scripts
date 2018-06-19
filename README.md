# Pfucking Shell Scripts

This is a straight-up rewrite of [Fucking Shell Scripts](https://github.com/brandonhilkert/fucking_shell_scripts) in Python.

"The easiest, most common sense server configuration management tool...because you just use fucking shell scripts."

# Features

*   AWS-only. EC2-classic only. More features will come when I need them.
*   This tool was originally designed to be insanely easy to use, and I left it that way

# What do?

Use this tool to configure an AWS base AMI by running shell scripts on it. It will spin up the instance, copy scripts to it, and run them. That's it.

# Installation
PFSS is a command-line tool that uses [Boto](https://github.com/boto/boto3). It has been tested on Ubuntu 15.10 with Python 3.4.3.

You will need to set up AWS auth as per the [boto documentation](https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration).

Grab the latest version and set it to executable like so:
```sh
sudo curl -o /usr/local/bin/pfss -L "https://github.com/megallo/pfss/releases/download/v1.0.0/pfss" && \
sudo chmod +x /usr/local/bin/pfss
```

# Setup

### Step 1: Create a project directory

```sh
mkdir config_management
```

Folder structure:

*   `/servers` _(required)_ - yaml server definitions _(see example below)_

*   `/scripts` _(required)_ - the shell scripts that will configure your servers _(see example below)_


An example folder structure:

```Shell
./config_management
├── scripts
│   ├── apt.sh
│   ├── deploy_key.sh
│   ├── git.sh
│   ├── redis.sh
│   ├── ruby2.sh
│   ├── rubygems.sh
│   ├── search_service_code.sh
│   └── search_service_env.sh
└── servers
    ├── defaults.yml
    └── search-server.yml
```


### Step 2: Create a server definition file

The server definition file defines how to build a type of server. Server definitions override settings in `defaults.yml`.

```YAML
# servers/search-server.yml
##################################################
# This file defines how to build our search server
##################################################

name: search-server
size: c1.xlarge
availability_zone: us-east-1d
image: ami-90374bf9
key_name: pd-app-server
private_key_path: /Users/yourname/.ssh/pd-app-server
security_groups: search-service  # override the security_groups defined in defaults.yml

###########################################
# Scripts needed to build the search server
###########################################

scripts:
  - scripts/apt.sh
  - scripts/search_service_env.sh
  - scripts/git.sh
  - scripts/ruby2.sh
  - scripts/rubygems.sh
  - scripts/redis.sh
  - scripts/deploy_key.sh
```

`servers/defaults.yml`has the same structure and keys a server definition file, **except**, you cannot define scripts or files.

```YAML
# servers/defaults.yml
################################
# This file defines our defaults
################################

security_groups: simple-group
size: c1.medium
image: ami-e76ac58e
availability_zone: us-east-1d
key_name: global-key

```

### Step 3: Add shell scripts that configure the server

Seriously...just write shell scripts.

Want to install Ruby 2? Here's an example:

```Shell
#!/bin/sh
#
# scripts/ruby2.sh
#
sudo apt-get -y install build-essential zlib1g-dev libssl-dev libreadline6-dev libyaml-dev
cd /tmp
wget http://ftp.ruby-lang.org/pub/ruby/2.0/ruby-2.0.0-p247.tar.gz
tar -xzf ruby-2.0.0-p247.tar.gz
cd ruby-2.0.0-p247
./configure --prefix=/usr/local
make
sudo make install
rm -rf /tmp/ruby*
```

### Step 4: Build/configure your server

```Shell
pfss search-server
```

This command does 2 things:

1.  Builds the new server
2.  Runs the scripts configuration

**HOLY SHIT! THAT WAS EASY.**

## Development
If you don't like my binary and want to build your own, you must have `virtualenv` installed. Then run
```sh
make all
```

## Contributing

1. Fork it
2. Create your feature branch (`git checkout -b my-new-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin my-new-feature`)
5. Create new Pull Request

