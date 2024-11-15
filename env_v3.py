from enum import Enum
class VariableError(Enum):
    TYPE_ERROR = 1
    NAME_ERROR = 2
    FAULT_ERROR = 3
class EnvironmentManager:
    def __init__(self):
        self.environment = []

    # We can define an error object here
    def get(self, symbol):
        cur_func_env = self.environment[-1]
        var_name = symbol.split(".")
        if len(var_name) > 1:
            struct_name = var_name[0]
            field_name = var_name[1]
            for env in reversed(cur_func_env):
                if struct_name in env:
                    struct = env[struct_name].value()
                    if not isinstance(struct, dict):
                        return VariableError.FAULT_ERROR
                    if field_name in struct:
                        return struct[field_name]
            return VariableError.FAULT_ERROR
        else:
            for env in reversed(cur_func_env):
                if symbol in env:
                    return env[symbol]
            return VariableError.NAME_ERROR

    def set(self, symbol, value):
        symbol_name = symbol.split(".")
        if len(symbol_name) > 1:
            struct_name = symbol_name[0]
            field_name = symbol_name[1]
            cur_func_env = self.environment[-1]
            for env in reversed(cur_func_env):
                if struct_name in env:
                    if env[struct_name] == None: 
                        return VariableError.FAULT_ERROR
                    struct = env[struct_name].value()
                    if field_name in struct:
                        struct[field_name] = value
                        return True
            return VariableError.FAULT_ERROR
        else:
            cur_func_env = self.environment[-1]
            for env in reversed(cur_func_env):
                if symbol in env:
                    env[symbol] = value
                    return True
            
            return VariableError.NAME_ERROR

    # create a new symbol in the top-most environment, regardless of whether that symbol exists
    # in a lower environment
    def create(self, symbol, value):
        cur_func_env = self.environment[-1]
        if symbol in cur_func_env[-1]:   # symbol already defined in current scope
            return False
        cur_func_env[-1][symbol] = value
        self.set(symbol, value)
        return True

    # used when we enter a new function - start with empty dictionary to hold parameters.
    def push_func(self):
        self.environment.append([{}])  # [[...]] -> [[...], [{}]]

    def push_block(self):
        cur_func_env = self.environment[-1]
        cur_func_env.append({})  # [[...],[{....}] -> [[...],[{...}, {}]]

    def pop_block(self):
        cur_func_env = self.environment[-1]
        cur_func_env.pop() 

    # used when we exit a nested block to discard the environment for that block
    def pop_func(self):
        self.environment.pop()

    def print_env(self):
        for env in self.environment:
            print(env)
            print("---")