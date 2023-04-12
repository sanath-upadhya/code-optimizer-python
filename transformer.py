import ast
from constant import *

known_pure = ["abs","aiter","all","any","anext","ascii","bin","bool","breakpoint","bytearray","bytes",
              "callable","chr","classmethod","compile","complex","delattr","dict","dir","divmod","enumerate",
              "eval","exec","filter","float","format","frozenset","getattr","globals","hasattr","hash","help",
              "hex","id","input","int","isinstance","issubclass","iter","len","list","locals","map","max","memoryview",
              "min","next","object","oct","open","ord","pow","print","property","range","repr","reversed","round",
              "tuple","type","vars","zip","__import__","set","setattr","slice","sorted","staticmethod","str","sum",
              "super"]

class Transformer(ast.NodeTransformer):
    def __init__(self, dependent_variable, flag):
        self.dependent_variables = dependent_variable
        """
        : flag = 0 => do nothing
        : flag = 1 => dependent variable
        : flag = 2 => pass
        """
        self.flag = flag

    #Special case needed to handle deletion of For statements.
    #We see all blocks inside for and remove all assignment for
    #variables that are not in dependent_variables
    def visit_For(self, node):
        if self.flag == TRANSFORMER_DEPENDENT_VARIABLES:
            remove_statement = []
            for i in range(0,len(node.body)):
                body = node.body[i]
                if isinstance(body, ast.Assign):
                    for target in body.targets:
                        if isinstance(target, ast.Name):
                            if target.id not in self.dependent_variables:
                                remove_statement.append(i)
                        elif isinstance(target, ast.Subscript):
                            if target.value.id not in self.dependent_variables:
                                remove_statement.append(i)
                elif isinstance(body, ast.AugAssign):
                    target = body.target
                    if target.id not in self.dependent_variables:
                        remove_statement.append(i)
                else:
                    pass
            i = 0
            for item in remove_statement:
                node.body.pop(item-i)
                i = i+1
            return node
        elif self.flag == TRANSFORMER_PASS:
            return None
        else:
            return node

    def visit_Assign(self, node):
        if self.flag == TRANSFORMER_DEPENDENT_VARIABLES:
            target_found_in_dependant = False
            for target in node.targets:
                target_name = ""
                if isinstance(target,ast.Name):
                    target_name = target.id
                elif isinstance(target,ast.Subscript):
                    target_name = target.value.id

                if target_name in self.dependent_variables:
                    target_found_in_dependant = True
                    break
            
            if target_found_in_dependant:
                return node
            else:
                return None
        elif self.flag == TRANSFORMER_PASS:
            return None
        else:
            return node
        
    def visit_AugAssign(self, node):
        if self.flag == TRANSFORMER_DEPENDENT_VARIABLES:
            target = node.target.id
            if target not in self.dependent_variables:
                return None
            else:
                return node
        elif self.flag == TRANSFORMER_PASS:
            return None
        else:
            return node
        
    
    def visit_Call(self,node):
        #check if function is pure or not. If pure and dependent variables
        #are not present, can delete the call
        function_name = node.func.id
        if function_name in known_pure and function_name !="print":
            keep_statement = False
            for argument in node.args:
                if argument in self.dependent_variables:
                    keep_statement = True
                    break
            if keep_statement:
                return node
            else:
                return None
        return node
    
    def visit_ListComp(self, node):
        target = node.elt
        if isinstance(target,ast.Name):
            if target.id not in self.dependent_variables:
                return None
        elif isinstance(target, ast.Call):
            if target.func.id not in self.dependent_variables:
                return None
        return node
    
    def visit_Expr(self,node):
        if self.flag == TRANSFORMER_DEPENDENT_VARIABLES:
            value = node.value
            if isinstance(value,ast.Call):
                #self.visit_Call(value)
                function_name = value.func.id
                if function_name in known_pure and function_name !="print":
                    keep_statement = False
                    for argument in value.args:
                        if argument in self.dependent_variables:
                            keep_statement = True
                            break
                    if keep_statement:
                        return node
                    else:
                        return None
                return node
            elif isinstance(value,ast.NamedExpr):
                if value.target.id not in self.dependent_variables:
                    return None
                else:
                    return node
            elif isinstance(value, ast.ListComp):
                target = value.elt
                if isinstance(target, ast.Call):
                    new_target = target.func.id
                    if new_target not in self.dependent_variables:
                        return None
                    else:
                        return node
                elif isinstance(value, ast.Name):
                    new_target = target.id
                    if new_target not in self.dependent_variables:
                        return None
                    else:
                        return node
                else:
                    return None
            else:
                return None
            
        elif self.flag == TRANSFORMER_PASS:
            return None
        else:
            return node
        
                
    def visit_Pass(self, node):
        if self.flag == TRANSFORMER_DEPENDENT_VARIABLES:
            return node
        elif self.flag == TRANSFORMER_PASS:
            return None
        else:
            return node
         