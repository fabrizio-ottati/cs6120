#! /usr/bin/env

import json, sys
from enum import Enum, auto
from typing import Sequence

OPS_THAT_COMMUTE = ("mul", "add", "and", "or")


class InstrType(Enum):
    LABEL = auto()
    EFFECT = auto()
    CONST = auto()
    VALUE = auto()
    CTRL = auto()


def load_prg():
    return json.loads(sys.stdin.read())


def get_instr_type(instr):
    if "label" in instr:
        return InstrType.LABEL
    if instr["op"] in ("br", "jmp"):
        return InstrType.CTRL
    if "dest" not in instr:
        return InstrType.EFFECT
    if instr["op"] == "const":
        return InstrType.CONST
    return InstrType.VALUE


def commutes(instr):
    return instr.get("op", None) in OPS_THAT_COMMUTE


def is_sequence_but_not_string(x):
    return isinstance(x, Sequence) and (not isinstance(x, (str, bytes, bytearray)))
