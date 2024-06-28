from pathlib import Path
from typing import List
from c2bf.parser.ast import ASTNode
from c2bf.parser.main import ProceduralParser
from c2bf.compile.spec import SPEC
from c2bf.utils import get_data_path


def parse_resolve_imports(script_path: str, import_common = False):
    script_path = str(Path(script_path).resolve())
    parser = ProceduralParser(SPEC)
    code = open(script_path, "r").read()
    if import_common:
        code = "import \"common\"\n" + code
    root = parser.parse(code)
    return ASTNode.transform(root, create_import_transformer(script_path, parser, [script_path]))

def create_import_transformer(source_path: str, parser: ProceduralParser, imported: List[str]):
    def transform_import(ast: ASTNode):
        if ast.name != "IMPORT":
            return
        import_path = orig_import_path = ast.literals[0].value[:-1].partition("\"")[2] + ".bfun"
        if import_path.startswith("."):
            import_path = Path(source_path).parent.joinpath(import_path)
        else:
            import_path = Path(get_data_path("lib")).joinpath(import_path)
        import_path = str(Path(import_path).resolve())

        if import_path in imported:
            return []
        imported.append(import_path)

        ast = parser.parse(f"\n\n# IMPORT: {orig_import_path} from {Path(source_path).name}\n" + open(import_path, "r").read().strip() + "\n")
        ast = ASTNode.transform(ast, create_import_transformer(import_path, parser, imported))
        return ast.children
    
    return transform_import
