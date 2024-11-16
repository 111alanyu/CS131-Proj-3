from intbase import InterpreterBase


# Enumerated type for our different language data types
class Type:
    INT = "int"
    BOOL = "bool"
    STRING = "string"
    NIL = "nil"
    STRUCT = "struct"
    VOID = "void"


# Represents a value, which has a type and its value
class Value:
    def __init__(self, type, value=None, struct_type=None):
        self.t = type
        self.v = value
        self.s = struct_type

    def value(self):
        return self.v

    def type(self):
        return self.t
    
    def struct_type(self):
        return self.s


def create_value(val):
    if val == InterpreterBase.TRUE_DEF:
        return Value(Type.BOOL, True)
    elif val == InterpreterBase.FALSE_DEF:
        return Value(Type.BOOL, False)
    elif val == InterpreterBase.NIL_DEF:
        return Value(Type.NIL, None)
    elif isinstance(val, str):
        return Value(Type.STRING, val)
    elif isinstance(val, int):
        return Value(Type.INT, val)
    elif isinstance(Type.VOID, val):
        return Value(Type.VOID, val)
    else:
        raise ValueError("Unknown value type")
    
def create_value_from_type(val_type, struct_type=None):
    if val_type == Type.BOOL:
        return Value(Type.BOOL, False)
    elif val_type == Type.INT:
        return Value(Type.INT, 0)
    elif val_type == Type.STRING:
        return Value(Type.STRING, "")
    elif val_type == Type.NIL:
        return Value(Type.NIL, None)
    elif val_type == Type.STRUCT:
        return Value(Type.STRUCT, {}, struct_type)
    else:
        raise ValueError("Unknown value type")


def get_printable(val):
    if val.type() == Type.INT:
        return str(val.value())
    if val.type() == Type.STRING:
        return val.value()
    if val.type() == Type.BOOL:
        if val.value() is True:
            return "true"
        return "false"
    if val.type() == Type.STRUCT:
        return "nil"
    if val.type() == Type.NIL:
        return "nil"
    return None
