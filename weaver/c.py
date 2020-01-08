from weaver.util import make_block
from weaver.auxiliary import reg_aux, StructRegAux


class C:
    def __init__(self):
        self.includes = set()
        self.func_impls = {}
        self.func_decls = {}
        self.text = []
        self.structs = set()
        self.regs = set()

    def write(self, func_line) -> str:
        text = ''
        for include in self.includes:
            text += f'#include {include}\n'
        text += '\n'
        for struct in self.structs:
            text += struct.create_aux().decl_type() + '\n\n'
        for func_impl in self.func_impls.values():
            text += func_impl.write_impl() + '\n\n'
        for func_decl in self.func_decls.values():
            text += func_decl.write_decl() + '\n\n'
        
        main_text = ''
        for reg in self.regs:
            assert not isinstance(reg_aux[reg], StructRegAux)
            main_text += reg_aux.decl(reg)
        main_text += '\n'.join(self.text)

        return text + func_line + ' ' + make_block(main_text)

    @staticmethod
    def merge(c1, c2):
        c = C()
        c.includes = c1.includes | c2.includes
        c.structs = c1.structs | c2.structs
        c.regs = c1.regs | c2.regs
        c.func_decls = {**c1.func_decls, **c2.func_decls}
        c.func_impls = {**c1.func_impls, **c2.func_impls}
        c.text = c1.text + c2.text
        return c


class FuncInfo:
    def __init__(self, name, args, ret_type, text_lines=None):
        self.name = name
        self.args = args
        self.ret_type = ret_type
        self.text_lines = text_lines

    def write_impl(self):
        assert self.text_lines is not None
        text = make_block("\n".join(self.text_lines))
        return f'{self.ret_type} {self.name}({",".join(self.args)}) {text}'

    def write_decl(self):
        return f'{self.ret_type} {self.name}({",".join(self.args)});'
