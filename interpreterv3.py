# document that we won't have a return inside the init/update of a for loop

import copy
from enum import Enum

from brewparse import parse_program
from env_v3 import EnvironmentManager, VariableError
from intbase import InterpreterBase, ErrorType
from type_valuev3 import Type, Value, create_value, get_printable, create_value_from_type


class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2

# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        self.__set_up_struct_table(ast)
        self.__set_up_function_table(ast)
        self.env = EnvironmentManager()
        self.__call_func_aux("main", [])

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            func_name = func_def.get("name")
            num_params = len(func_def.get("args"))
            if func_name not in self.func_name_to_ast:
                self.func_name_to_ast[func_name] = {}
            self.func_name_to_ast[func_name][num_params] = func_def
            if func_def.get("return_type") not in self.struct_name_to_ast and func_def.get("return_type") not in [Type.INT, Type.STRING, Type.BOOL, Type.VOID]:
                super().error(ErrorType.TYPE_ERROR, f"Unknown return type {func_def.get('return_type')}")
            func_args = func_def.get("args")
            for arg in func_args:
                if arg.get("var_type") not in self.struct_name_to_ast and arg.get("var_type") not in [Type.INT, Type.STRING, Type.BOOL]:
                    super().error(ErrorType.TYPE_ERROR, f"Unknown argument type {arg.get('var_type')}")

    def __get_func_by_name(self, name, num_params):
        if name not in self.func_name_to_ast:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        candidate_funcs = self.func_name_to_ast[name]
        if num_params not in candidate_funcs:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {name} taking {num_params} params not found",
            )
        return candidate_funcs[num_params]
    
    def __set_up_struct_table(self, ast):
        self.struct_name_to_ast = {}
        for struct_def in ast.get("structs"):
            struct_name = struct_def.get("name")
            fields = struct_def.get("fields")
            if struct_name in self.struct_name_to_ast:
                super().error(ErrorType.TYPE_ERROR, f"Duplicate struct definition: {struct_name}")
            self.struct_name_to_ast[struct_name] = {
                "fields": {field.get("name"): field.get("var_type") for field in fields},
                "ast": struct_def
            }

    def __run_statements(self, statements):
        self.env.push_block()
        for statement in statements:
            if self.trace_output:
                print(statement)
            status, return_val = self.__run_statement(statement)
            if status == ExecStatus.RETURN:
                self.env.pop_block()
                return (status, return_val)

        self.env.pop_block()
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __run_statement(self, statement):
        status = ExecStatus.CONTINUE
        return_val = None
        if statement.elem_type == InterpreterBase.FCALL_NODE:
            self.__call_func(statement)
        elif statement.elem_type == "=":
            self.__assign(statement)
        elif statement.elem_type == InterpreterBase.VAR_DEF_NODE:
            self.__var_def(statement)
        elif statement.elem_type == InterpreterBase.RETURN_NODE:
            status, return_val = self.__do_return(statement)
        elif statement.elem_type == Interpreter.IF_NODE:
            status, return_val = self.__do_if(statement)
        elif statement.elem_type == Interpreter.FOR_NODE:
            status, return_val = self.__do_for(statement)

        return (status, return_val)
    
    def __call_func(self, call_node):
        func_name = call_node.get("name")
        actual_args = call_node.get("args")
        return self.__call_func_aux(func_name, actual_args)

    def __call_func_aux(self, func_name, actual_args):
        if func_name == "print":
            return self.__call_print(actual_args)
        if func_name == "inputi" or func_name == "inputs":
            return self.__call_input(func_name, actual_args)

        func_ast = self.__get_func_by_name(func_name, len(actual_args))
        formal_args = func_ast.get("args")
        expected_return_type = func_ast.get("return_type")
        if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            )

        # first evaluate all of the actual parameters and associate them with the formal parameter names
        args = {}
        for formal_ast, actual_ast in zip(formal_args, actual_args):
            result = copy.copy(self.__eval_expr(actual_ast))
            result_type = None
            if result.type() == Type.STRUCT:
                result_type = result.struct_type()
            else: 
                result_type = result.type()
            if formal_ast.get("var_type") != result_type:
                if formal_ast.get("var_type") == Type.BOOL and result_type == Type.INT:
                    result = Value(Type.BOOL, result.value() != 0)
                elif formal_ast.get("var_type") in self.struct_name_to_ast and result_type == Type.NIL:
                    pass
                else:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Expected type {formal_ast.get('var_type')}, got {result_type}",
                    )
            
            arg_name = formal_ast.get("name")
            args[arg_name] = result

        # then create the new activation record 
        self.env.push_func()
        # and add the formal arguments to the activation record
        for arg_name, value in args.items():
          self.env.create(arg_name, value)
        _, return_val = self.__run_statements(func_ast.get("statements"))
        self.env.pop_func()

        # Check if the expected return value is VOID. If it is, check that the return value is NIL.
        # If the return value IS NIL, then return VOID (since there is special handling). 
        # Otherwise, throw an error.
        if expected_return_type == InterpreterBase.VOID_DEF:
            if return_val == Interpreter.NIL_VALUE:
                return Type.VOID
            else:
                super().error(ErrorType.TYPE_ERROR, f"Expected return type {expected_return_type}, got {return_val.type()}")
        print("EXPECTED RETURN TYPE", expected_return_type)
        if expected_return_type == Type.INT and return_val.type() == Type.NIL:
            return Value(Type.INT, 0)
        elif expected_return_type == Type.STRING and return_val.type() == Type.NIL:
            return Value(Type.STRING, "")
        elif expected_return_type == Type.BOOL and return_val.type() == Type.NIL:
            return Value(Type.BOOL, False)
        elif expected_return_type == Type.BOOL and return_val.type() == Type.INT:
            return Value(Type.BOOL, return_val.value() != 0)
        elif expected_return_type in self.struct_name_to_ast and return_val.type() == Type.NIL:
            return Value(Type.NIL, create_value_from_type(Type.NIL))
        elif expected_return_type != return_val.type() and not (return_val.type() == Type.STRUCT and return_val.struct_type() == expected_return_type):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Expected return type {expected_return_type}, got {return_val.type()}",
            )
        elif expected_return_type not in self.struct_name_to_ast and return_val.type() == Type.STRUCT:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Expected return type {expected_return_type}, got {return_val.type()}",
            )
        # If the expected return value is not VOID, then check that the return value is of the expected type.

        return return_val

    def __call_print(self, args):
        output = ""
        for arg in args:
            result = self.__eval_expr(arg)  # result is a Value object
            output = output + get_printable(result)
        super().output(output)
        return Interpreter.NIL_VALUE

    def __call_input(self, name, args):
        if args is not None and len(args) == 1:
            result = self.__eval_expr(args[0])
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if name == "inputi":
            return Value(Type.INT, int(inp))
        if name == "inputs":
            return Value(Type.STRING, inp)

    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        value_obj = self.__eval_expr(assign_ast.get("expression"))
        value_type = value_obj.type()
        assign_variable = self.env.get(var_name)

        # Handle the case where the variable is a field of a struct and it is not initalized
        if assign_variable == VariableError.NAME_ERROR:
            super().error(
                ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment"
            )
        elif assign_variable == VariableError.FAULT_ERROR:
            super().error(
                ErrorType.FAULT_ERROR, f"Attempt to access field of nil object"
            )
        assign_variable_type = assign_variable.type()

        # TODO: This feels wrong. But the struct error should be caught by the if statement on 208
        if assign_variable_type != value_type and (assign_variable_type != Type.STRUCT) and not (assign_variable_type == Type.BOOL and value_type == Type.INT):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Expected type {assign_variable_type}, got {value_obj.type()}",
            )
        if assign_variable_type == Type.BOOL and value_type == Type.INT:
            value_obj = Value(Type.BOOL, value_obj.value() != 0)

        ret = self.env.set(var_name, value_obj)
        if ret == VariableError.NAME_ERROR:
            super().error(
                ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment"
            )
        elif ret == VariableError.FAULT_ERROR:
            super().error(
                ErrorType.FAULT_ERROR, f"Attempt to access field of nil object"
            )
        

    def __var_def(self, var_ast):
        var_name = var_ast.get("name")
        var_type = var_ast.get("var_type")
        value = None

        if var_type in self.struct_name_to_ast:
            value = create_value_from_type(Type.STRUCT, var_type)
        
        elif var_type == Type.INT:
            value = create_value_from_type(Type.INT)
        elif var_type == Type.STRING:
            value = create_value_from_type(Type.STRING)
        elif var_type == Type.BOOL:
            value = create_value_from_type(Type.BOOL)
        else: # Unknown type 
            super().error(
                ErrorType.TYPE_ERROR, f"Unknown type {var_type} in variable definition"
            )

        status = self.env.create(var_name, value)
        if not status:
            super().error(
                ErrorType.NAME_ERROR, f"Duplicate definition for variable {var_name}"
            )
        
    def __eval_expr(self, expr_ast):
        if expr_ast.elem_type == InterpreterBase.NIL_NODE:
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_NODE:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_NODE:
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_NODE:
            return Value(Type.BOOL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.VAR_NODE:
            var_name = expr_ast.get("name")
            val = self.env.get(var_name)
            if val == VariableError.NAME_ERROR:
                super().error(ErrorType.NAME_ERROR, f"Undefined variable {var_name}")
            elif val == VariableError.FAULT_ERROR:
                super().error(ErrorType.FAULT_ERROR, f"Attempt to access field of nil object")
            elif val == VariableError.TYPE_ERROR:
                super().error(ErrorType.TYPE_ERROR, f"Attempt to access field of non-struct object")
            return val
        if expr_ast.elem_type == InterpreterBase.FCALL_NODE:
            return self.__call_func(expr_ast)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)
        if expr_ast.elem_type == Interpreter.NEG_NODE:
            return self.__eval_neg_unary(expr_ast, Type.INT, lambda x: -1 * x)
        if expr_ast.elem_type == Interpreter.NOT_NODE:
            return self.__eval_not_unary(expr_ast, [Type.BOOL, Type.INT], lambda x: not x)
        if expr_ast.elem_type == Interpreter.NEW_NODE:
            struct_name = expr_ast.get("var_type")
            if struct_name not in self.struct_name_to_ast:
                super().error(ErrorType.TYPE_ERROR, f"Unknown struct type {struct_name}")
            struct_def = self.struct_name_to_ast[struct_name]
            fields = {}
            for field_name, field_type in struct_def["fields"].items():
                if field_type in self.struct_name_to_ast:
                    field_type = Type.STRUCT
                fields[field_name] = create_value_from_type(field_type)
            return Value(Type.STRUCT, fields, struct_name)

    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))
        if not self.__compatible_types(
            arith_ast.elem_type, left_value_obj, right_value_obj
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {left_value_obj.type()}",
            )
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        return f(left_value_obj, right_value_obj)

    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        
        # TODO: Should I just return false here? 
        if obj1 == Type.VOID or obj2 == Type.VOID:
            return False

        obj1_type = obj1.type()
        obj2_type = obj2.type()
        if oper == "==" or oper == "!=":
            # Ints can be compared to other ints and bools (coercision)
            if (obj1_type == Type.INT and obj2_type == Type.BOOL) or (obj1_type == Type.INT and obj2_type == Type.INT):
                return True
            # Strings can be compared to other strings
            if (obj1_type == Type.STRING) and (obj2_type == Type.STRING):
                return True
            # Bools can be compared to other bools and ints (coercision)
            if (obj1_type == Type.BOOL and obj2_type == Type.BOOL) or (obj1_type == Type.BOOL and obj2_type == Type.INT):
                return True
            # Structs can be compared to other structs and nil
            if (obj1_type == Type.STRUCT and obj2_type == Type.STRUCT) or (obj1_type == Type.STRUCT and obj2_type == Type.NIL):
                return True
            # Nil can be compared to nil and structs
            if (obj1_type == Type.NIL and obj2_type == Type.NIL) or (obj1_type == Type.NIL and obj2_type == Type.STRUCT):
                return True
            return False

        if oper == "&&" or oper == "||":
            if (obj1_type == Type.BOOL and obj2_type == Type.BOOL) or (obj1_type == Type.BOOL and obj2_type == Type.INT) or\
                  (obj1_type == Type.INT and obj2_type == Type.BOOL) or (obj1_type == Type.INT and obj2_type == Type.INT):
                return True
            return False
        
        if oper in ["<", "<=", ">", ">=", "+", "-", "*", "/"]:
            if obj1_type == Type.INT and obj2_type == Type.INT:
                return True
            return False
        
        return False
    

    def __eval_neg_unary(self, arith_ast, t, f):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
        if value_obj.type() != t:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible type for {arith_ast.elem_type} operation",
            )
        return Value(t, f(value_obj.value()))


    def __eval_not_unary(self, arith_ast, t, f):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
        if value_obj.type() not in t:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible type for {arith_ast.elem_type} operation",
            )
        if value_obj.type() == Type.INT:
            value_obj = Value(Type.BOOL, value_obj.value() != 0)

        return Value(Type.BOOL, f(value_obj.value()))

    def __setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
        self.op_to_lambda[Type.INT]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.INT]["-"] = lambda x, y: Value(
            x.type(), x.value() - y.value()
        )
        self.op_to_lambda[Type.INT]["*"] = lambda x, y: Value(
            x.type(), x.value() * y.value()
        )
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: Value(
            x.type(), x.value() // y.value()
        )
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()\
                or (y.type() == Type.BOOL and (x.value() != 0) == y.value())
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value() \
                or (y.type() == Type.BOOL and (x.value() != 0) != y.value())

        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
        self.op_to_lambda[Type.INT]["||"] = lambda x, y: Value(
            Type.BOOL, bool(x.value() or y.value())
        )
        self.op_to_lambda[Type.INT]["&&"] = lambda x, y: Value(
            Type.BOOL, bool(x.value() and y.value())
        )
        #  set up operations on strings
        self.op_to_lambda[Type.STRING] = {}
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        #  set up operations on bools
        self.op_to_lambda[Type.BOOL] = {}
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            x.type(), x.value() and y.value()
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            x.type(), x.value() or y.value()
        )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value() \
            or (y.type() == Type.INT and x.value() == (y.value() != 0) )
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, not(x.type() == y.type() and x.value() == y.value() \
            or (y.type() == Type.INT and x.value() == (y.value() != 0) ))
        )

        #  set up operations on nil
        self.op_to_lambda[Type.NIL] = {}
        self.op_to_lambda[Type.NIL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.NIL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

        #  set up operations on structs 
        self.op_to_lambda[Type.STRUCT] = {}
        self.op_to_lambda[Type.STRUCT]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() is y.value() or (y.type() == Type.NIL and x.value() == {})
        )
        self.op_to_lambda[Type.STRUCT]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() is not y.value() or (y.type() == Type.NIL and x.value() != {})
        )

        # TODO: This should error out
        """
        self.op_to_lambda[Type.STRUCT]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.STRUCT]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        """

    def __do_if(self, if_ast):
        cond_ast = if_ast.get("condition")
        result = self.__eval_expr(cond_ast)
        if result.type() != Type.BOOL and result.type() != Type.INT:
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible type for if condition",
            )
        if result.type() == Type.INT:
            result = Value(Type.BOOL, result.value() != 0)
        if result.value():
            statements = if_ast.get("statements")
            status, return_val = self.__run_statements(statements)
            return (status, return_val)
        else:
            else_statements = if_ast.get("else_statements")
            if else_statements is not None:
                status, return_val = self.__run_statements(else_statements)
                return (status, return_val)

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_for(self, for_ast):
        init_ast = for_ast.get("init") 
        cond_ast = for_ast.get("condition")
        update_ast = for_ast.get("update") 

        self.__run_statement(init_ast)  # initialize counter variable
        run_for = Interpreter.TRUE_VALUE
        while run_for.value():
            run_for = self.__eval_expr(cond_ast)  # check for-loop condition
            if run_for.type() != Type.BOOL and run_for.type() != Type.INT:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for for condition",
                )
            if run_for.value():
                statements = for_ast.get("statements")
                status, return_val = self.__run_statements(statements)
                if status == ExecStatus.RETURN:
                    return status, return_val
                self.__run_statement(update_ast)  # update counter variable

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_return(self, return_ast):
        expr_ast = return_ast.get("expression")
        if expr_ast is None:
            return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
        value_obj = copy.copy(self.__eval_expr(expr_ast))
        return (ExecStatus.RETURN, value_obj)


if __name__ == "__main__":
    program = """
struct s {
  a:int;
}

func main() : int {
  var x: s;
  x = new s;
  x = nil;
  print(x.a);
}

"""
    interpreter = Interpreter(trace_output=False)
    interpreter.run(program)
