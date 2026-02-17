#! /usr/bin/env python3

from dataclasses import dataclass, field
from typing import Sequence
from collections import defaultdict
from utils import get_instr_type, InstrType, commutes
from utils import is_sequence_but_not_string


class LVNTable:
    def __init__(
        self,
    ):
        # [((op, *args), canonical_var)]
        self.table: list[tuple[tuple[str, Sequence[int]], str]] = []
        self.var2valn_map: dict = dict()
        self.defs: list = []
        self.body: list = []
        self.prefix: defaultdict = defaultdict(int)
        self.globvars: set = set()
        self.glob2local: dict = dict()
        return

    # Utilities to generate values.

    def build_val(self, instr):
        # Check for identities.
        op = instr.get("op", None)
        if op == "id":
            idvar = instr["args"][0]
            valn = self.var2valn(idvar)
            val = self.table[valn][0]
            return val

        if op == "const":
            return ["const", instr["type"], instr["value"]]

        args = self.var2valn(instr["args"])
        if commutes(instr):
            args.sort()

        return [instr["op"], *args]

    # Utilities to access the table.

    def var2valn(self, var):
        if is_sequence_but_not_string(var):
            return [self.var2valn_map[x] for x in var]
        return self.var2valn_map[var]

    def valn2var(self, valn):
        if is_sequence_but_not_string(valn):
            return [self.table[x][-1] for x in valn]
        return self.table[valn][-1]

    def find_val(self, val):
        for i, (tval, tvar) in enumerate(self.table):
            if tval == val:
                return i
        return None

    def find_instr(self, instr):
        val = self.build_val(instr)
        idx = self.find_val(val)
        return idx

    # Utilities to modify the table.

    def add_instr_to_table(self, instr):
        idx = self.find_instr(instr)
        if idx is None:
            val = self.build_val(instr)
            self.table.append([val, instr["dest"]])
            idx = len(self.table) - 1
        self.var2valn_map[instr["dest"]] = idx
        return idx

    def add_instr(self, instr):
        instr_type = get_instr_type(instr)
        if instr_type in (InstrType.LABEL, InstrType.EFFECT, InstrType.CTRL):
            return None
        if instr_type not in (InstrType.VALUE, InstrType.CONST):
            raise ValueError(f"Invalid instruction: {instr}.")

        globvars = self.get_globvars(instr)
        for v in globvars.difference(self.globvars):
            self.add_globvar(v)
        if "args" in instr:
            instr["args"] = [
                self.glob2local[v] if v in self.globvars else v for v in instr["args"]
            ]

        dest = instr["dest"]
        if dest in self.defs:
            # Rename old variables.
            new_name = self.new_name(dest)
            while new_name in self.defs:
                new_name = self.new_name(dest)
            # Table.
            valn = self.var2valn(dest)
            if self.table[valn][-1] == dest:
                self.table[valn][-1] = new_name
            self.var2valn_map[new_name] = self.var2valn(dest)
            for i, _instr in enumerate(self.body):
                if _instr.get("dest", None) == dest:
                    self.body[i]["dest"] = new_name
                if dest in _instr.get("args", []):
                    self.body[i]["args"] = [
                        (new_name if arg == dest else arg) for arg in _instr["args"]
                    ]
            if dest in self.glob2local:
                self.glob2local[dest] = new_name
        elif dest in self.globvars:
            # New name.
            new_name = self.new_name(dest)
            while new_name in self.defs:
                new_name = self.new_name(dest)
            self.defs.append(new_name)
            instr["dest"] = new_name
            self.glob2local[dest] = new_name
        else:
            self.defs.append(dest)

        return self.add_instr_to_table(instr)

    # Renaming of variables previously defined.

    def new_name(self, var):
        name = f"lvn.{self.prefix[var]}"
        self.prefix[var] += 1
        return name

    # Global variables utilities.

    def get_globvars(self, instr):
        is_globvar = lambda v: v not in self.defs
        return set(v for v in instr.get("args", []) if is_globvar(v))

    def add_globvar(self, v):
        val = ["globval", v]
        idx = self.find_val(val)
        if idx is None:
            self.table.append([val, v])
            idx = len(self.table) - 1
            self.glob2local[v] = v
            self.globvars.add(v)
        self.var2valn_map[v] = idx
        return idx

    # Instruction generation starting from the table.

    def build_ctrl_instr(self, instr):
        if instr["op"] == "jmp":
            return instr

        new_instr = dict(instr)
        if instr["op"] == "br":
            condition = instr["args"][0]
            cond_valn = self.var2valn(condition)
            new_instr["args"][0] = self.valn2var(cond_valn)
        return new_instr

    # FIXME
    def build_effect_instr(self, instr):
        if instr.get("op", None) == "print":
            valn = self.var2valn(instr["args"][0])
            var = self.valn2var(valn)
            instr["args"][0] = var
        return instr

    def build_value_instr(self, instr):
        new_instr = dict(instr)
        dest = new_instr["dest"]
        idx = self.find_instr(instr)
        var = self.table[idx][-1]
        if dest == var:
            # For each argument, build the value and find the associated
            # canonical variable.
            new_instr["args"] = self.valn2var(self.var2valn(new_instr["args"]))
        else:
            # Returning an `id` operation to the canonical home of the value.
            new_instr["op"] = "id"
            new_instr["args"] = [var]
        return new_instr

    def build_const_instr(self, instr):
        new_instr = dict(instr)
        dest = new_instr["dest"]
        idx = self.find_instr(instr)
        var = self.table[idx][-1]
        if var != dest:
            new_instr["op"] = "id"
            new_instr["args"] = [var]
            del new_instr["value"]
        return new_instr

    def build_instr(self, instr):
        self.add_instr(instr)
        instr_type = get_instr_type(instr)
        if instr_type == InstrType.LABEL:
            new_instr = instr
        elif instr_type == InstrType.EFFECT:
            new_instr = self.build_effect_instr(instr)
        elif instr_type == InstrType.CTRL:
            new_instr = self.build_ctrl_instr(instr)
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
    for instr in body:
        lvn_table.build_instr(instr)
    new_body = lvn_table.get_body()
    # Updating global variables.
    for v in lvn_table.globvars:
        if lvn_table.glob2local[v] != v:
            var = lvn_table.glob2local[v]
            var = lvn_table.table[lvn_table.var2valn(var)][-1]
            new_body.append(dict(op="id", dest=v, args=[var]))

    return new_body, lvn_table


def lvn_prg(prg):
    import cfg

    prg = cfg.get_cfg(prg)
    for fn in prg["functions"]:
        for block in fn["cfg"]:
            block["instrs"], _ = lvn_block(block["instrs"])
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
