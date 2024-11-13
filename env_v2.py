# The EnvironmentManager class keeps a mapping between each variable name (aka symbol)
# in a brewin program and the Value object, which stores a type, and a value.

from type_valuev2 import Type, Value, create_value, get_printable

class EnvironmentManager:
    def __init__(self):
        self.environment = []

    # returns a VariableDef object
    def get(self, symbol):
        cur_func_env = self.environment[-1]
        for env in reversed(cur_func_env):
            if symbol in env:
                return env[symbol]

        return None

    def set(self, symbol, value):
        cur_func_env = self.environment[-1]
        for env in reversed(cur_func_env):
            if symbol in env:
                env[symbol] = value
                return True

        return False

    # create a new symbol in the top-most environment, regardless of whether that symbol exists
    # in a lower environment
    def create(self, symbol, value, var_type):
        cur_func_env = self.environment[-1]
        if symbol in cur_func_env[-1]:   # symbol already defined in current scope
            return 1
        cur_func_env[-1][symbol] = value
        
        if var_type == "int":
            self.set(symbol, create_value(0))
        elif var_type == "bool":
            self.set(symbol, create_value(False))
        elif var_type == "str":
            self.set(symbol, create_value(""))
        else:
            return 2
        
        return 0

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