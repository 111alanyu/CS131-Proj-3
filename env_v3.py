from enum import Enum
class VariableError(Enum):
    TYPE_ERROR = 1
    NAME_ERROR = 2
    FAULT_ERROR = 3
    DEBUG_ERROR = 4
class EnvironmentManager:
    def __init__(self):
        self.environment = []

    # We can define an error object here

    """
    1. Get variable from top level environment
    2. Get variable from strcut (the variable is defined in the struct)
    3. Get variable from struct in struct ... (here, the variable IS DEFINED IN THE STRUCT, no top level varialb)
    
    Fault error if the field is not found, name error if the struct is not initalized?
    """
    # TODO: need to re-write this for struct of structs

    def get(self, symbol):
        cur_func_env = self.environment[-1]
        var_name = symbol.split(".")
        # 1. This is just a variable in a top level environment
        if len(var_name) == 0:
            print("ERROR!", symbol)
        elif len(var_name) == 1:
            for env in reversed(cur_func_env):
                if symbol in env:
                    return env[symbol]
            return VariableError.NAME_ERROR
        
        # 2. This is a variable in a struct
        elif len(var_name) == 2:
            struct_name = var_name[0]
            field_name = var_name[1]
            for env in reversed(cur_func_env):
                if struct_name in env:
                    struct = env[struct_name]
                    struct = struct.value()
                    if not isinstance(struct, dict):
                        if struct is None:
                            return VariableError.FAULT_ERROR
                        else:
                            return VariableError.TYPE_ERROR
                    elif struct == {}: # this happens
                        return VariableError.FAULT_ERROR
                    if field_name in struct:
                        return struct[field_name]
            return VariableError.NAME_ERROR
        else:
            struct_name = var_name[0]
            field_name = var_name[1]
            # Find the struct in the environment
            for env in reversed(cur_func_env):
                # we found the struct, so let's find the field now
                if struct_name in env:
                    struct = env[struct_name].value()
                    var_name.pop(0)
                    while len(var_name) >= 1:
                        if not isinstance(struct, dict):
                            if struct is None:
                                return VariableError.FAULT_ERROR
                            else:
                                return VariableError.TYPE_ERROR
                        elif struct == {}:
                            return VariableError.FAULT_ERROR
                        if field_name in struct:
                            value = struct[field_name]
                            if len(var_name) == 1:
                                return value
                            struct = value.value()
                            var_name.pop(0)
                            field_name = var_name[0]
            return VariableError.NAME_ERROR



    def set(self, symbol, value):
        cur_func_env = self.environment[-1]
        var_name = symbol.split(".")
        # 1. This is just a variable in a top level environment
        if len(var_name) == 0:
            print("ERROR!", symbol)
        elif len(var_name) == 1:
            for env in reversed(cur_func_env):
                if symbol in env:
                    env[symbol] = value
                    return
            return VariableError.NAME_ERROR
        
        # 2. This is a variable in a struct
        elif len(var_name) == 2:
            struct_name = var_name[0]
            field_name = var_name[1]
            for env in reversed(cur_func_env):
                if struct_name in env:
                    struct = env[struct_name].value()
                    if not isinstance(struct, dict):
                        if struct is None:
                            return VariableError.FAULT_ERROR
                        else:
                            return VariableError.TYPE_ERROR
                    elif struct == {}:
                        return VariableError.FAULT_ERROR
                    if field_name in struct:
                        struct[field_name] = value
                        return
                    return VariableError.FAULT_ERROR
            return VariableError.NAME_ERROR
        
        else:
            struct_name = var_name[0]
            field_name = var_name[1]
            # Find the struct in the environment
            for env in reversed(cur_func_env):
                # we found the struct, so let's find the field now
                if struct_name in env:
                    struct = env[struct_name].value()
                    var_name.pop(0)
                    while len(var_name) >= 1:
                        if not isinstance(struct, dict):
                            if struct is None:
                                return VariableError.FAULT_ERROR
                            else:
                                return VariableError.TYPE_ERROR
                        elif struct == {}:
                            return VariableError.FAULT_ERROR
                        if field_name in struct:
                            if len(var_name) == 1:
                                struct[field_name] = value
                                return
                            var_name.pop(0)
                            struct = struct[field_name].value()
                            field_name = var_name[0]
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