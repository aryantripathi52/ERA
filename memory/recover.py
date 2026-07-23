import marshal
import dis

with open(r"e:\LASTER\memory\memory_manager.pyc", "rb") as f:
    f.seek(16) # Skip the magic number and timestamp for Python 3.3+
    code_obj = marshal.load(f)

with open(r"e:\LASTER\memory\disassembly.txt", "w", encoding="utf-8") as out:
    def dump_code(c, indent=""):
        out.write(f"{indent}Name: {c.co_name}\n")
        out.write(f"{indent}Constants: {c.co_consts}\n")
        out.write(f"{indent}Names: {c.co_names}\n")
        out.write(f"{indent}Varnames: {c.co_varnames}\n")
        out.write(f"{indent}--- Disassembly ---\n")
        dis.dis(c, file=out)
        out.write("\n")
        for const in c.co_consts:
            if hasattr(const, 'co_code'):
                dump_code(const, indent + "    ")
    dump_code(code_obj)
