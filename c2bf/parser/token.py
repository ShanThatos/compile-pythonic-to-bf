

class Token:
    INSTANCE_COUNT = 0

    def __init__(self, name: str, value: str, whitespace: str = " "):
        self.name = name
        self.value = value
        self.whitespace = whitespace
        self.id = Token.INSTANCE_COUNT
        Token.INSTANCE_COUNT += 1
    
    def __str__(self) -> str:
        return self.whitespace + self.value
    def __repr__(self) -> str:
        return f"Token({repr(self.name)}, {repr(self.value)}, {repr(self.whitespace)})"
