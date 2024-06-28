
from typing import List, Callable, Optional, Union, overload

from .token import Token

type ASTNodeTransformer = Callable[["ASTNode"], Union["ASTNode", List["ASTNode"], None]]

class ASTNode:
    def __init__(self, name: str, children: List["ASTNode"] = []):
        self.name = name
        self.children = children
        self.parent: Optional[ASTNode] = None
        self.index = -1
        self.index_children()
    
    def __repr__(self):
        return f"ASTNode({repr(self.name)}, {repr(self.children)})"
    
    def __iter__(self):
        yield self
        for child in self.children:
            yield from iter(child)

    @property
    def literals(self):
        return [x.token for x in self if isinstance(x, ASTLiteral)]

    @property
    def literal(self) -> Token:
        if not isinstance(self, ASTLiteral):
            raise Exception("ASTNode is not a literal")
        return self.token

    @property
    def root(self):
        rt = self
        while rt.parent is not None:
            rt = rt.parent
        return rt

    @property
    def next_sibling(self):
        if self.parent is None: 
            return None
        if self.index + 1 < len(self.parent.children):
            return self.parent.children[self.index + 1]
        return None

    def get(self, name: str, idx: int = 0):
        o_idx = idx
        for child in self.children:
            if child.name == name:
                if idx == 0:
                    return child
                idx -= 1
        raise Exception(f"Could not find child with name {name} and index {o_idx}")
    
    def get_all(self, name: str):
        return [child for child in self.children if child.name == name]
    

    @overload
    def __getitem__(self, __i: int) -> "ASTNode": ...
    @overload
    def __getitem__(self, __s: slice) -> List["ASTNode"]: ...

    def __getitem__(self, idx):
        return self.children[idx]


    def index_children(self):
        for i, child in enumerate(self.children):
            child.parent = self
            child.index = i
            child.index_children()

    def to_string(self):
        return "".join(str(x.token) for x in self if isinstance(x, ASTLiteral))


    def transform_tree(self, transformer: ASTNodeTransformer):
        transformed = False
        ast = self
        self.index_children()
        i = 0
        while i < len(ast.children):
            new_ast = transformer(ast.children[i])
            if isinstance(new_ast, list):
                transformed = True
                ast.children[i:i+1] = new_ast
            elif isinstance(new_ast, ASTNode):
                transformed = True
                ast.children[i] = new_ast
            else:
                i += 1
                continue
            if transformed:
                self.index_children()
        
        for child in ast.children:
            transformed |= child.transform_tree(transformer)
        return transformed

    @classmethod
    def transform(cls, root: "ASTNode", transformer: ASTNodeTransformer):
        root.index_children()
        new_root = transformer(root)
        if new_root is not None:
            assert(isinstance(new_root, ASTNode))
            root = new_root
        root.index_children()
        root.transform_tree(transformer)
        return root


class ASTLiteral(ASTNode):
    def __init__(self, name: str, token: Token):
        super().__init__(name)
        self.token = token
    
    def __repr__(self):
        return f"ASTLiteral({repr(self.name)}, {repr(self.token)})"

