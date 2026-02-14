#! /usr/bin/env python3

"""
FIXME: This description is not up to date. Ignore it.

The scope of local value numbering (LVN) is to use values, not variables,
when analizing programs.
Each instruction computes/generates a value. A value is associate to a tuple
`(operation, *operands)`.

We can imagine the LVN table as:

 ________________________________________________________________________
|             |       |                                                  |
| value index | value | canonical variable in the code holding the value |
|_____________|_______|__________________________________________________|
|             |       |                                                  |

The following is the algorithm for creating the table.

```
lvn_table = create_empty_table()
new_block = []
var_ptrs = {}
for instr in block:
    if instr generates a value:
        val_idxs = [lvn_table.find_val_idx(operand) for operand in operands]
        val_tuple = (instr.op, *val_idxs)
        if val_tuple in lvn_table:
            new_block += (instr.dest = id lvn_table.find_var(val_tuple))
        else:
            # The value tuple is associated with the variable.
            lvn_table.add_val_var(val_tuple, instr.dest)
            new_instr = replace_args_with_vals(lvn_table, instr)
            new_block += new_instr
        var_ptrs[instr.dest] = lvn_table.find_val(val_tuple)
return new_block
```
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Sequence
from collections import defaultdict


class InstrType(Enum):
    LABEL = auto()
    EFFECT = auto()
    CONST = auto()
    VALUE = auto()


class LVNTable:
    # [((op, *args), canonical_var)]
    table: list[tuple[tuple[str, Sequence[int]], str]] = []
    var2valn: dict = dict()
    var2name: dict = dict()
    defs: list = []
    body: list = []

    def find_val(self, val):
        for i, (tval, tvar) in enumerate(self.table):
            if tval == val:
                return i
        return None

    def build_val(self, instr):
        args = self.get_valn(instr["args"])
        args.sort()
        return [instr["op"], *args]

    def get_instr_type(self, instr):
        if "label" in instr:
            return InstrType.LABEL
        if "dest" not in instr:
            return InstrType.EFFECT
        if instr["op"] == "const":
            return InstrType.CONST
        return InstrType.VALUE

    def add_const_instr(self, instr):
        dest = instr["dest"]
        val = ["const", instr["value"]]
        idx = self.find_val(val)
        if idx is not None:
            self.var2valn[dest] = idx
            return idx
        self.table.append([val, dest])
        idx = len(self.table) - 1
        # self.valn2var[idx] = dest
        self.var2valn[dest] = idx
        return idx

    def add_value_instr(self, instr):
        dest = instr["dest"]
        val = self.build_val(instr)
        idx = self.find_val(val)
        if idx is not None:
            self.var2valn[dest] = idx
            return idx

        self.table.append([val, dest])
        idx = len(self.table) - 1
        # self.valn2var[idx] = dest
        self.var2valn[dest] = idx
        return idx

    def add_instr(self, instr):
        instr_type = self.get_instr_type(instr)
        # FIXME: We have to substitute also the args!
        if instr_type in (InstrType.LABEL, InstrType.EFFECT):
            return None

        dest = instr["dest"]
        if dest in self.defs:
            # Rename old variables.
            new_name = dest
            while new_name in self.defs:
                new_name = "%" + new_name
            # Table.
            valn = self.var2valn[dest]
            if self.table[valn][-1] == dest:
                self.table[valn][-1] = new_name
            self.var2valn[new_name] = self.var2valn[dest]
            del self.var2valn[dest]
            for i, _instr in enumerate(self.body):
                if _instr.get("dest", None) == dest:
                    self.body[i]["dest"] = new_name
                if dest in _instr.get("args", []):
                    self.body[i]["args"] = [
                        (new_name if arg == dest else arg) for arg in _instr["args"]
                    ]
            self.defs.append(new_name)
        else:
            self.defs.append(dest)

        if instr_type == InstrType.CONST:
            return self.add_const_instr(instr)
        if instr_type == InstrType.VALUE:
            return self.add_value_instr(instr)
        raise ValueError(f"Invalid instruction: {instr}.")

    def get_valn(self, args):
        return [self.var2valn[arg] for arg in args]

    def valn2var(self, valns):
        return [self.table[valn][-1] for valn in valns]

    def build_effect_instr(self, instr):
        new_instr = dict(instr)
        new_instr["args"] = self.valn2var(self.get_valn(new_instr["args"]))
        return new_instr

    def build_value_instr(self, instr):
        new_instr = dict(instr)
        dest = new_instr["dest"]
        val = self.build_val(instr)
        idx = self.find_val(val)
        var = self.table[idx][-1]
        if dest == var:
            # For each argument, build the value and find the associated
            # canonical variable.
            new_instr["args"] = self.valn2var(self.get_valn(new_instr["args"]))
        else:
            # Returning an `id` operation to the canonical home of the value.
            new_instr["op"] = "id"
            new_instr["args"] = [var]
        return new_instr

    def build_const_instr(self, instr):
        new_instr = dict(instr)
        dest = new_instr["dest"]
        val = ["const", instr["value"]]
        idx = self.find_val(val)
        var = self.table[idx][-1]
        if var != dest:
            new_instr["op"] = "id"
            new_instr["args"] = [var]
            del new_instr["value"]
        return new_instr

    def build_instr(self, instr):
        self.add_instr(instr)
        instr_type = self.get_instr_type(instr)
        if instr_type == InstrType.LABEL:
            new_instr = instr
        elif instr_type == InstrType.EFFECT:
            new_instr = self.build_effect_instr(instr)
        elif instr_type == InstrType.CONST:
            new_instr = self.build_const_instr(instr)
        elif instr_type == InstrType.VALUE:
            new_instr = self.build_value_instr(instr)
        else:
            raise ValueError(f"Invalid instruction: {instr}.")
        self.body.append(new_instr)
        return

    def get_body(self):
        return self.body


def lvn_block(body):
    lvn_table = LVNTable()
    new_body = []
    for instr in body:
        lvn_table.build_instr(instr)
    return lvn_table.get_body()


def lvn_prg(prg):
    import cfg

    prg = cfg.get_cfg(prg)
    for fn in prg["functions"]:
        for block in fn["cfg"]:
            block["instrs"] = lvn_block(block["instrs"])
    prg = cfg.cfg2bril(prg)
    return prg


def main():
    from utils import load_prg
    import json

    prg = load_prg()
    prg = lvn_prg(prg)
    print(json.dumps(prg))
    return


if __name__ == "__main__":
    main()
