#! /usr/bin/env python

TERMINATORS = (
    "br",
    "jmp",
    "ret",
)
DEBUG = False


def is_label(instr):
    # FIXME
    return len(instr.keys()) == 1 and instr.get("label", False)


def get_block_name(first_instr, i):
    if is_label(first_instr):
        ret = first_instr["label"]
    else:
        ret = f"#b{i}"
        i += 1
    return ret, i


def form_cfg(body, bnum):
    cfg = []

    # Handling empty function.
    if len(body) == 0:
        cfg = [dict(name="#b0", instrs=[], succs=[])]
        return cfg, bnum

    new_block = True
    for i, instr in enumerate(body):
        if new_block or is_label(instr):
            bname, bnum = get_block_name(instr, bnum)
            cfg.append(dict(name=bname, instrs=[], succs=[]))
            # Handle fallthrough from previous block
            if is_label(instr):
                fallthrough = cfg[-2]["instrs"][-1] not in TERMINATORS
                if fallthrough and bname not in cfg[-2]["succs"]:
                    cfg[-2]["succs"].append(bname)
            new_block = False

        if instr.get("op", "not_an_op") in TERMINATORS:
            if instr["op"] in ("br", "jmp"):
                # FIXME
                cfg[-1]["succs"] = instr["args"][1:]
            new_block = True
        cfg[-1]["instrs"].append(instr)
    return cfg, bnum


def cfg2bril(cfg):
    from copy import copy

    prg = copy(cfg)
    for i, fn in enumerate(cfg["functions"]):
        instrs = []
        for block in fn["cfg"]:
            instrs += block["instrs"]
        prg["functions"][i]["instrs"] = instrs[:]
        del prg["functions"][i]["cfg"]
    return prg


def create_left_justified_label(text):
    lines = [line for line in text.split("\n") if line.strip()]
    rows = "".join(f'  <TR><TD ALIGN="LEFT">{line}</TD></TR>\n' for line in lines)
    html_label = f'<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">\n{rows}</TABLE>'
    return html_label


def cfg2dot(fname: str, cfg):
    import pydot

    g = pydot.Dot(fname, graph_type="digraph")
    for block in cfg:
        node_txt = ""
        for instr in block["instrs"]:
            instr_txt = json2bril(instr)
            node_txt += instr_txt + "\n"
        node = pydot.Node(
            block["name"],
            label=f"<{create_left_justified_label(node_txt)}>",
            shape="plaintext",
            xlabel=block["name"],
        )
        g.add_node(node)
        for succ in block["succs"]:
            e = pydot.Edge(block["name"], succ)
            g.add_edge(e)
    return g


def json2bril(instr):
    import sys

    sys.path.append("../../bril/bril-txt")
    import briltxt

    if is_label(instr):
        instr_txt = f".{instr['label']}:"
    else:
        instr_txt = briltxt.instr_to_string(instr)
    return instr_txt


def get_cfg(prg):
    """
    Creates a CFG out of a `bril` program.
    The CFG program is:
    {
        "functions": [
            {
                "name": ...,
                "args": ...,
                "type": ...,
                "instrs": [...],
                "cfg": [
                    {
                        "bname": ...,
                        "instrs: [...],
                        "succs": [...],
                    }
                ]
            }
        ]
    }
    """
    cfg_prg = []
    bnum = 0
    for fn in prg["functions"]:
        cfg_prg.append(fn)
        cfg, bnum = form_cfg(fn["instrs"], bnum)
        cfg_prg[-1]["cfg"] = cfg
    cfg_prg = dict(functions=cfg_prg)
    return cfg_prg


def main():
    import json

    prg = load_prg()
    cfg_prg = get_cfg(prg)
    if DEBUG:
        for fn in cfg_prg["functions"]:
            graph = cfg2dot(fn["name"], fn["cfg"])
            graph.write_png(f"{fn['name']}_graph.png")
    print(json.dumps(cfg_prg))
    return


if __name__ == "__main__":
    main()
