#! /usr/bin/env python3


def build_const_instr(instr, val):
    instr["op"] = "const"
    instr["value"] = val
    return instr


def cfold_instr(instr, lvn_table):
    from utils import InstrType, get_instr_type

    instr_type = get_instr_type(instr)
    if instr_type == InstrType.LABEL:
        return instr, False

    args = instr.get("args", [])
    op = instr.get("op", None)

    cval = lambda _instr, _val: ["const", _instr["type"], _val]

    if instr_type == InstrType.VALUE and len(args) > 1:
        valn0 = lvn_table.var2valn(args[0])
        valn1 = lvn_table.var2valn(args[1])
        val0 = lvn_table.table[valn0][0]
        val1 = lvn_table.table[valn1][0]

        if op in ("eq", "ge", "le", "gt", "lt"):
            if val0 == val1:
                if op in ("eq", "ge", "le"):
                    instr = build_const_instr(instr, True)
                if op in ("gt", "lt"):
                    instr = build_const_instr(instr, False)
                return instr, True
            if val0[0] == val1[0] == "const":
                if op == "eq":
                    instr = build_const_instr(instr, val0[-1] == val1[-1])
                if op == "ge":
                    instr = build_const_instr(instr, val0[-1] >= val1[-1])
                if op == "le":
                    instr = build_const_instr(instr, val0[-1] <= val1[-1])
                if op == "gt":
                    instr = build_const_instr(instr, val0[-1] > val1[-1])
                if op == "lt":
                    instr = build_const_instr(instr, val0[-1] < val1[-1])
                return instr, True

        if op in ("add", "mul", "div", "sub", "and", "or"):
            fn = {
                "add": lambda a, b: a + b,
                "mul": lambda a, b: a * b,
                "sub": lambda a, b: a - b,
                "div": lambda a, b: a // b,
                "and": lambda a, b: a and b,
                "or": lambda a, b: a or b,
            }[op]
            if val0[0] == val1[0] == "const":
                constval = fn(val0[-1], val1[-1])
                instr = build_const_instr(instr, constval)
                return instr, True

        if op in ("and", "or"):
            if op == "and":
                if val0 == cval(instr, False) or val1 == cval(instr, False):
                    instr = build_const_instr(instr, False)
                    return instr, True
            if op == "or":
                if val0 == cval(instr, True) or val1 == cval(instr, True):
                    instr = build_const_instr(instr, True)
                    return instr, True

    if instr_type == InstrType.VALUE and op == "not":
        valn = lvn_table.var2valn(args[0])
        val = lvn_table.table[valn][0]
        if val[0] == "const":
            instr = build_const_instr(instr, not val[-1])
            return instr, True

    if instr_type == InstrType.CTRL and op == "br":
        valn = lvn_table.var2valn(args[0])
        val = lvn_table.table[valn][0]
        if val[0] == "const":
            instr["op"] = "jmp"
            instr["args"] = [args[1] if val[-1] else args[2]]
            return instr, True

    return instr, False


def cfold_block(body):
    from lvn import lvn_block

    glb_changed = True
    new_body = body
    while glb_changed:
        body, lvn_table = lvn_block(new_body)
        glb_changed = False
        new_body = []
        for instr in body:
            new_instr, changed = cfold_instr(instr, lvn_table)
            glb_changed |= changed
            new_body.append(new_instr)
    return new_body


def cfold_prg(prg):
    from cfg import get_cfg, cfg2bril

    prg = get_cfg(prg)
    for fn in prg["functions"]:
        for block in fn["cfg"]:
            block["instrs"] = cfold_block(block["instrs"])
    prg = cfg2bril(prg)
    return prg


def main():
    from utils import load_prg
    import json

    prg = load_prg()
    prg = cfold_prg(prg)
    print(json.dumps(prg))
    return


if __name__ == "__main__":
    main()
