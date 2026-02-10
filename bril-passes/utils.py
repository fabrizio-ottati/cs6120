#! /usr/bin/env

import json, sys


def load_prg():
    return json.loads(sys.stdin.read())
