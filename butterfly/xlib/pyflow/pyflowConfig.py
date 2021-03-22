#
# pyFlow - a lightweight parallel task engine
#
# Copyright (c) 2012-2017 Illumina, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
#

"""
pyflowConfig

This file defines a class instance 'siteConfig' containing pyflow components
which are the most likely to need site-specific configuration.
"""

import os


# this is the only object pyflow needs to import, it
# is defined at the end of this module:
#
siteConfig = None


# depending on network setup getfqdn() can be slow, so cache calls to this function here:
#
def _getHostName():
    import socket
    return socket.getfqdn()


cachedHostName = None


def getHostName():
    global cachedHostName
    if cachedHostName is None:
        cachedHostName = _getHostName()
    return cachedHostName


def getDomainName():
    hn = getHostName().split(".")
    if len(hn) > 1:
        hn = hn[1:]
    return ".".join(hn)


class DefaultSiteConfig(object):
    """
    Default configuration settings are designed to work with as
    many sites as technically feasible
    """

    # Default memory (in megabytes) requested by each command task:
    #
    defaultTaskMemMb = 2048

    # In local run mode, this is the defalt memory per thread that we
    # assume is available:
    #
    defaultHostMemMbPerCore = 2048

    # both getHostName and getDomainName are used in the
    # siteConfig factory, so these are not designed to be
    # overridden at present:
    getHostName = staticmethod(getHostName)
    getDomainName = staticmethod(getDomainName)


def getEnvVar(key):
    if key in os.environ:
        return os.environ[key]
    return None
siteConfig = DefaultSiteConfig()
