#! /usr/bin/env

import json, sys
from enum import Enum, auto


class InstrType(Enum):
    LABEL = auto()
    EFFECT = auto()
    CONST = auto()
    VALUE = auto()


def load_prg():
    return json.loads(sys.stdin.read())


def get_instr_type(instr):
    if "label" in instr:
        return InstrType.LABEL
    if "dest" not in instr:
        return InstrType.EFFECT
    if instr["op"] == "const":
        return InstrType.CONST
    return InstrType.VALUE
