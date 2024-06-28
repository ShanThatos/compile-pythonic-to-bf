from c2bf.compile.bfun.compilers.utils import new_label, parse_code
from c2bf.parser.main import tab_all_lines
from c2bf.parser.ast import ASTNode


def transform_forloops(root_ast: ASTNode):
    def transform_forloop(ast: ASTNode):
        if not (ast.name == "statement" and ast[0].name == "loop_statement" and ast[0][0].name == "for_statement"):
            return

        ast = ast[0][0]
        loop_var = ast.get("REF").literal.value
        iter_lbl = new_label(ast, f"loop_iter")

        loop_code = [
            f"\n{loop_var} = 0",
            f"{iter_lbl}:",
            f"{iter_lbl} = ({ast.get("expression").to_string().strip()}).$iter()",
            f"while ({iter_lbl}.$has_next()) {{",
            f"    {loop_var} = {iter_lbl}.$next()",
            tab_all_lines(ast.get("statement").to_string().strip(), "    "),
            f"}}",
        ]
        return parse_code("\n".join(loop_code)).children

    ASTNode.transform(root_ast, transform_forloop)
