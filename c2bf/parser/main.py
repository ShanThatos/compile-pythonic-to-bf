import re
import copy
from typing import Dict, List, Optional, Tuple, Callable, TypeVar

from .token import Token
from .ast import ASTNode, ASTLiteral

T = TypeVar('T')
def flatten(x: List[T] | T) -> List[T]:
    if isinstance(x, list):
        return sum((flatten(e) for e in x), [])
    return [x]

def point_out_index(code: str, index: int, token_length: int = 1, before: int = 5, after: int = 5):
    code = f"\n{code}\n"
    index += 1
    
    line_start = code.rfind("\n", 0, index)
    line_end = code.find("\n", index)

    main_line_start = line_start
    main_line_end = line_end

    for _ in range(before):
        line_start = code.rfind("\n", 0, line_start)
        if line_start == -1:
            line_start = 0
            break
    for _ in range(after):
        line_end = code.find("\n", line_end + 1)
        if line_end == -1:
            line_end = len(code)
            break
    
    first_half = code[line_start:main_line_end] + "\n"
    pointer_line = " " * (index - main_line_start - 1) + "^" * token_length
    second_half = code[main_line_end:line_end]
    
    result = first_half + pointer_line + second_half
    return result.rstrip()

def tab_all_lines(code: str, tab: str) -> str:
    return "\n".join((tab + line for line in code.split("\n")))


class ProceduralLexer:
    def __init__(self, reserved_tokens: List[str], regex_matches: List[Tuple[str, str]] = []) -> None:
        self.res = list(sorted(reserved_tokens, key=lambda x: -len(x)))
        self.rgx = regex_matches
    
    def tokenize(self, code: str) -> List[Token]:
        tokens = []
        current = 0
        while current < len(code):
            whitespace_start = current
            while current < len(code) and code[current].isspace():
                current += 1
            whitespace_end = current
            token_whitespace = code[whitespace_start:whitespace_end]

            if current >= len(code):
                tokens.append(Token("==END==", "", token_whitespace))
                break

            token_name = None
            token_value = None
            for special_token in self.res:
                if special_token.isalpha():
                    if match := re.match(fr"{re.escape(special_token)}\b", code[current:]):
                        token_name = special_token
                        token_value = special_token
                        break
                elif code.startswith(special_token, current):
                    token_name = special_token
                    token_value = special_token
                    break
            else:
                for rgx_type, rgx_match in self.rgx:
                    if match := re.match(rgx_match, code[current:]):
                        token_name = rgx_type
                        token_value = match.group(0)
                        break
            
            if token_name is None or token_value is None:
                raise Exception("Unknown token: \n\n" + point_out_index(code, current, before=500, after=500))

            tokens.append(Token(token_name, token_value, token_whitespace))
            current += len(token_value)
        else:
            tokens.append(Token("==END==", "", ""))
        return tokens


class ParseError(Exception):
    def __init__(self, message: str, tokens: List[Token], index: int):
        super().__init__()
        self.message = message
        self.tokens = tokens
        self.index = index
    
    def __add__(self, other: "ParseError"):
        return ParseError(self.message + "\n" + tab_all_lines(other.message, "  "), other.tokens, other.index)
    
    def __str__(self) -> str:
        token = self.tokens[self.index]
        code_first_half = "".join(str(x) for x in self.tokens[:self.index]) + token.whitespace
        code_second_half = token.value + "".join(str(x) for x in self.tokens[self.index+1:])
        location_message = point_out_index(code_first_half + code_second_half, len(code_first_half), token_length=len(token.value), before=100, after=30)
        location_message = tab_all_lines(location_message, "    ")
        return f"Parse Error: \n{location_message}\n\n{self.message}"

class ProceduralParser:
    def __init__(self, syntax: Dict[str, List], start: str = "program"):
        self.original_syntax = copy.deepcopy(syntax)
        self.syntax = copy.deepcopy(syntax)
        self.start = start
        self.directives = {
            "ONE_OF": self.__parse_directive_one_of, 
            "REPEAT": self.__parse_directive_repeat, 
            "OPTIONAL": self.__parse_directive_optional,
            "FORWARD": self.__parse_directive_forward,
            "PASS": self.__parse_directive_pass,
            "DELIMITER": self.__parse_directive_delimiter
        }
        self.find_regex_matches()
        self.find_reserved_tokens()


    def traverse_syntax_tree(self, callback: Callable[[str | list], bool | None]):
        open_set: List[str | list] = [self.start]
        closed_set = set()
        while open_set:
            current = open_set.pop()
            if isinstance(current, str):
                if current in closed_set or current in self.directives:
                    continue
                closed_set.add(current)
            if callback(current):
                continue
            if isinstance(current, str) and current in self.syntax:
                open_set.append(self.syntax[current])
            elif isinstance(current, list):
                open_set.extend(current)

    def find_regex_matches(self):
        self.regex_matches = []
        regex_matches = []
        def callback(current):
            if isinstance(current, str) and current in self.syntax and not any(current == x[0] for x in regex_matches):
                if len(x := self.syntax[current]) == 2 and x[0] == "REGEX_MATCH":
                    regex_matches.append((current, x[1]))
                    return True
        self.traverse_syntax_tree(callback)
        self.regex_matches = [(x[0], x[1][1]) for x in sorted(regex_matches, key=lambda x: x[1][0])]

        for rgx_type, _ in self.regex_matches:
            self.syntax.pop(rgx_type)

    def find_reserved_tokens(self):
        reserved = []
        def callback(current):
            if isinstance(current, str) and current not in self.syntax and not any(current == x[0] for x in self.regex_matches):
                reserved.append(current)
        self.traverse_syntax_tree(callback)
        self.reserved_tokens = list(sorted(reserved, key=lambda x: -len(x)))


    def parse(self, code: str):
        code = code.replace("\t", "    ")
        lexer = ProceduralLexer(self.reserved_tokens, self.regex_matches)
        tokens = lexer.tokenize(code)

        self.tokens = tokens
        self.index = 0
        ast = self.__parse_all(self.start)
        assert(isinstance(ast, ASTNode))
        return ast


    @property
    def current(self) -> Optional[Token]:
        return self.tokens[self.index] if self.ready else None
    @property
    def ready(self) -> bool:
        return self.index < len(self.tokens) and self.tokens[self.index].name != "==END=="

    def error(self, message: str, index: Optional[int] = None):
        return ParseError(message, self.tokens, self.index if index is None else index)

    def __parse_all(self, syntax: str) -> ASTNode | List[ASTNode]:
        ast = self.__parse(syntax)
        if self.ready:
            raise self.error("Expected end of file")
        return ast
    
    def __parse(self, syntax: str | List) -> ASTNode | List[ASTNode]:
        if isinstance(syntax, str):
            return self.__parse_str(syntax)
        elif isinstance(syntax, list):
            return self.__parse_list(syntax)
    
    def __parse_str(self, syntax: str) -> ASTNode:
        if syntax in self.syntax:
            saved_index = self.index
            try:
                return ASTNode(syntax, self.__parse_list(self.syntax[syntax]))
            except ParseError as pe:
                raise self.error(f"Expected '{syntax}'", saved_index) + pe
        token = self.current
        if token is None:
            raise self.error(f"Expected '{syntax}' found end of file")
        if not self.ready or token.name != syntax:
            raise self.error(f"Expected '{syntax}' found {repr(token)}")
        self.index += 1
        return ASTLiteral(syntax, token)

    def __parse_list(self, syntax: List) -> List[ASTNode]:
        index = 0
        children = []
        while index < len(syntax):
            item = syntax[index]
            if isinstance(item, str) and item in self.directives:
                result = self.directives[item](syntax[index := index + 1])
            else:
                result = self.__parse(item)
            children.append(result)
            index += 1
        return flatten(children)

    def __parse_directive_one_of(self, syntax: List) -> ASTNode | List[ASTNode]:
        if not isinstance(syntax, list) or len(syntax) == 0:
            raise self.error(f"SPEC Error: Expected list of options for ONE_OF directive")
        
        saved_index = self.index
        best_error = None
        for choice in syntax:
            try:
                self.index = saved_index
                result = self.__parse(choice)
                if best_error is not None and self.index < best_error.index:
                    raise best_error
                return result
            except ParseError as pe:
                if best_error is None or pe.index > best_error.index:
                    best_error = pe
        if best_error is None:
            raise self.error(f"Expected one of {syntax}")
        self.index = best_error.index
        raise best_error

    def __parse_directive_repeat(self, syntax: str | List) -> ASTNode | List[ASTNode]:
        children = []
        while self.ready:
            saved_index = self.index
            try:
                children.append(self.__parse(syntax))
            except ParseError:
                if self.index == saved_index:
                    break
                raise
        return flatten(children)

    def __parse_directive_optional(self, syntax: str | List) -> ASTNode | List[ASTNode]:
        return self.__parse(["ONE_OF", [syntax, []]])

    def __parse_directive_forward(self, syntax: str) -> ASTNode | List[ASTNode]:
        if syntax not in self.syntax:
            raise self.error(f"SPEC Error: Unknown syntax '{syntax}' used in FORWARD directive")
        return self.__parse(self.syntax[syntax])

    def __parse_directive_pass(self, syntax: str | List) -> ASTNode | List[ASTNode]:
        self.__parse(syntax)
        return []

    def __parse_directive_delimiter(self, syntax: list) -> ASTNode | List[ASTNode]:
        if not isinstance(syntax, list) or len(syntax) != 2:
            raise self.error(f"SPEC Error: Expected list of length 2 for DELIMITER directive, got {syntax}")
        unit_syntax, delimiter = syntax
        return self.__parse([unit_syntax, "REPEAT", [delimiter, unit_syntax]])

