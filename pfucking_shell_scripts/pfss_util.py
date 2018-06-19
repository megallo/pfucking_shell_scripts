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
from __future__ import absolute_import
import os
from datetime import datetime, timezone

import pureyaml

from pfucking_shell_scripts.pfss_const import SERVERS_DIR


def load_server_config(filename: str) -> dict:
    config_path = os.path.join(SERVERS_DIR, filename + '.yml')
    with open(config_path) as f:
        return pureyaml.load(f)


def log_prefix_factory(command_name: str):
    def log_prefix():
        return '{0:%Y-%m-%d %H:%M:%S %Z} [{1}]'.format(datetime.now(timezone.utc), command_name)
    return log_prefix


def default_datetime(obj):
    if isinstance(obj, datetime):
        if obj.utcoffset() is not None:
            obj = obj - obj.utcoffset()
    return str(obj)


# OMG SHUT UP

class NullLogger(object):
    def __init__(self, f):
        pass

    def __getattribute__(self, name):
        return self

    def __call__(self, *args, **kwargs):
        return self


import ply.yacc
ply.yacc.PlyLogger = NullLogger
