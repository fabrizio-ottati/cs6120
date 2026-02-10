#! /usr/bin/env python3

import click

global_changed = False


def dead_defs_pass(body):
    from collections import defaultdict

    global global_changed

    changed = True
    while changed:
        to_delete = []
        uses = defaultdict(int)
        for instr in body:
            # Skip constant definitions.
            # Using `get` to skip instructions that do not have an `op` field.
            if instr.get("op", "const") != "const":
                # Using `get` to skip instructions that do not have an `args` field.
                for arg in instr.get("args", []):
                    uses[arg] += 1
        for i, instr in enumerate(body):
            if "dest" in instr and uses[instr["dest"]] == 0:
                to_delete.append(i)
        body = [instr for i, instr in enumerate(body) if i not in to_delete]
        changed = len(to_delete) > 0
        if changed:
            global_changed = True
    return body


def killed_defs_block(body):
    """
    A definition is killed if it is re-defined without being used.
    Example:

    ```bril
    a: int = const 42
    b: int = const 24
    c: int = const 2
    d: int = add b, c
    a: int = const 3
    e: int = add a, d
    ```

    The first definition of `a` is never used before being redefined. The
    condition for a killed definition is, given a variable `a`:
    - meet a definition of `a`.
    - `a` has been defined before.
    - between the two definitions, `a` has not been used.
    Then, you can remove the first definition of `a`.
    """
    from collections import defaultdict

    global global_changed

    changed = True
    while changed:
        uses = defaultdict(int)
        defs = {}
        to_delete = []
        for i, instr in enumerate(body):
            if instr.get("op", "const") != "const":
                for arg in instr.get("args", []):
                    uses[arg] += 1
            if "dest" in instr:
                if instr["dest"] in defs and instr["dest"] not in uses:
                    to_delete.append(defs[instr["dest"]])
                defs[instr["dest"]] = i
        body = [instr for i, instr in enumerate(body) if i not in to_delete]
        changed = len(to_delete) > 0
        if changed:
            global_changed = True
    return body


def killed_defs_pass(prg):
    from cfg import get_cfg, cfg2bril

    cfg = get_cfg(prg)
    for fn in cfg["functions"]:
        for i, block in enumerate(fn["cfg"]):
            fn["cfg"][i]["instrs"] = killed_defs_block(block["instrs"])
    prg = cfg2bril(cfg)
    return prg


def tdce_fn(fn, **kwargs):
    if kwargs.get("dead_defs", False):
        fn["instrs"] = dead_defs_pass(fn["instrs"])
    return fn


def tdce_prg(prg, **kwargs):
    prg["functions"] = [tdce_fn(fn, **kwargs) for fn in prg["functions"]]
    if kwargs.get("killed_defs", False):
        prg = killed_defs_pass(prg)
    return prg


def tdce(**kwargs):
    from utils import load_prg
    import json

    global global_changed

    prg = load_prg()
    global_changed = True
    while global_changed:
        global_changed = False
        prg = tdce_prg(prg, **kwargs)
    print(json.dumps(prg))
    return


@click.command()
@click.option("--all-opts", is_flag=True)
@click.option("--dead-defs", is_flag=True)
@click.option("--killed-defs", is_flag=True)
def main(all_opts, dead_defs, killed_defs):
    tdce(dead_defs=dead_defs or all_opts, killed_defs=killed_defs or all_opts)
    return


if __name__ == "__main__":
    main()
