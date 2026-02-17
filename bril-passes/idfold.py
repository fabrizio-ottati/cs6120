#! /usr/bin/env python3


def build_id_instr(instr, arg):
    instr["op"] = "id"
    instr["args"] = [arg]
    return instr


def idfold_instr(instr, lvn_table):
    from utils import InstrType, get_instr_type

    instr_type = get_instr_type(instr)
    if instr_type == InstrType.LABEL:
        return instr, False

    args = instr.get("args", [])
    op = instr.get("op", None)

    cval = lambda _instr, _val: ["const", _instr["type"], _val]

    if instr_type == InstrType.VALUE and op == "id":
        valn0 = lvn_table.var2valn(args[0])
        val0 = lvn_table.table[valn0][0]

    if instr_type == InstrType.VALUE and len(args) > 1:
        valn0 = lvn_table.var2valn(args[0])
        valn1 = lvn_table.var2valn(args[1])
        val0 = lvn_table.table[valn0][0]
        val1 = lvn_table.table[valn1][0]

        if op == "add":
            if val0 == cval(instr, 0):
                instr = build_id_instr(instr, args[1])
                return instr, True
            if val1 == cval(instr, 0):
                instr = build_id_instr(instr, args[0])
                return instr, True
        if op == "mul":
            if val0 == cval(instr, 1):
                instr = build_id_instr(instr, args[1])
                return instr, True
            if val1 == cval(instr, 1):
                instr = build_id_instr(instr, args[0])
                return instr, True
        if op == "div":
            if val1 == cval(instr, 1):
                instr = build_id_instr(instr, args[0])
                return instr, True
        if op == "sub":
            if val1 == cval(instr, 0):
                instr = build_id_instr(instr, args[0])
                return instr, True
        if op in ("and", "or"):
            if val0 == val1:
                instr = build_id_instr(instr, args[0])
                return instr, True

    return instr, False


def idfold_block(body):
    from lvn import lvn_block

    glb_changed = True
    new_body = body
    while glb_changed:
        glb_changed = False
        body, lvn_table = lvn_block(new_body)
        new_body = []
        for instr in body:
            new_instr, changed = idfold_instr(instr, lvn_table)
            glb_changed |= changed
            new_body.append(new_instr)
    return new_body


def idfold_prg(prg):
    from cfg import get_cfg, cfg2bril

    prg = get_cfg(prg)
    for fn in prg["functions"]:
        for block in fn["cfg"]:
            block["instrs"] = idfold_block(block["instrs"])
    prg = cfg2bril(prg)
    return prg


def main():
    from utils import load_prg
    import json

    # from sys import stderr
    # print((80 * "-"), file=stderr)
    # print("Running id folding...", file=stderr)
    # print((80 * "-"), file=stderr)
    prg = load_prg()
    prg = idfold_prg(prg)
    print(json.dumps(prg))
    return


if __name__ == "__main__":
    main()
