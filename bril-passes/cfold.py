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

    if args:
        valn0 = lvn_table.var2valn[args[0]]
        valn1 = lvn_table.var2valn[args[1]]
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
                    instr = build_const_instr(instr, val0[1] == val1[1])
                if op == "ge":
                    instr = build_const_instr(instr, val0[1] >= val1[1])
                if op == "le":
                    instr = build_const_instr(instr, val0[1] <= val1[1])
                if op == "gt":
                    instr = build_const_instr(instr, val0[1] > val1[1])
                if op == "lt":
                    instr = build_const_instr(instr, val0[1] < val1[1])
                return instr, True
    return instr, False


def cfold_block(body):
    from lvn import lvn_block

    body, lvn_table = lvn_block(body)
    glb_changed = True
    while glb_changed:
        glb_changed = False
        new_body = []
        for instr in body:
            new_instr, changed = cfold_instr(instr, lvn_table)
            glb_changed |= changed
            new_body.append(new_instr)
    # new_body, _ = lvn_block(body)
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
