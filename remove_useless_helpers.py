'''
All the helper functions needed by the remove_useless()
'''

from transformer import *
from ast_helpers import *

'''
Function to update the dependent_variable list. This keeps track of
all the useful variables for any block
'''
def add_value_to_dependent_variable(dependent_variables, value):
    if value not in dependent_variables:
        dependent_variables.append(value)

'''
Function returns True if node has a dependent variable within
it
'''
def check_if_variables_are_dependent(node, dependent_variables):
    node_generator = ast.walk(node)
    for child_node in node_generator:
        if(isinstance(child_node,ast.Name)):
            if child_node.id in dependent_variables:
                return True
            
    return False


'''
Get all the dependent variables. Used in the handling of
ast.Assign object
'''
def get_dependent_variables(dependent_variables, node):
    if (isinstance(node,ast.Name)):
        add_value_to_dependent_variable(dependent_variables, node.id)

    elif (isinstance(node,ast.BinOp)):
        get_dependent_variables(dependent_variables,node.left)
        get_dependent_variables(dependent_variables,node.right)

    elif (isinstance(node,ast.NamedExpr)):
        get_dependent_variables(dependent_variables,node.value)
        if check_if_variables_are_dependent(node.value, dependent_variables):
            get_dependent_variables(dependent_variables,node.target)

    elif (isinstance(node, ast.Call)):
        check_pure_function = check_if_function_pure(node.func.id)
        if not check_pure_function:
            add_value_to_dependent_variable(dependent_variables, node.func.id)
            for argument in node.args:
                get_dependent_variables(dependent_variables, argument)

    return

'''
Check if the node has a NamedExpr in it
'''
def check_if_subtree_has_named_expr(node):
    node_generator = ast.walk(node)
    for child_node in node_generator:
        if (isinstance(child_node,ast.NamedExpr)):
            return True
    
    return False


'''
Get all the global variables in the module
'''
def get_global_variables(tree, global_variables):
    for block in reversed(tree.body):
        if (isinstance(block, ast.Assign)):
            global_variables.append(block.targets[0].id) 

'''
Check if the function is pure or not
'''
def check_if_function_pure(function_name):
    if function_name in known_pure and function_name != PRINT_FUNCTION_CALL:
        #looks like function is pure. 
        return True
    else:
        return False

'''
Function to handle the case for ast.Call object
'''    
def remove_useless_function_call(tree, dependant_variables):
    #need to add args only function is impure. Check if function
    #is pure or not
    check_pure_function = check_if_function_pure(tree.func.id)
    if not check_pure_function:
        add_value_to_dependent_variable(dependant_variables, tree.func.id)
        for argument in tree.args:
            remove_useless_in_block(argument, dependant_variables)


'''
Function to handle the case for ast.FuncDef object
'''
def remove_useless_function_definition(tree, dependant_variables):
    for argument in tree.args.args:
        add_value_to_dependent_variable(dependant_variables,argument.arg)

    for statement in reversed(tree.body):
        remove_useless_in_block(statement, dependant_variables)

'''
Function to handle the case for ast.For object
'''
def remove_useless_for(tree, dependant_variables):

    for block in tree.body:
        remove_useless_in_block(block, dependant_variables)
 
'''
Function to handle the case for ast.While object
'''
def remove_useless_while(tree, dependant_variables):
    #get the operators in the while loop and add to dependant
    remove_useless_in_block(tree.test, dependant_variables)

    #Then iterate over all the statements in both directions
    for block in tree.body:
        remove_useless_in_block(block, dependant_variables)

    for block in reversed(tree.body):
         remove_useless_in_block(block, dependant_variables)

'''
Function to handle the case for ast.If object
'''
def remove_useless_if(tree, dependant_variables):
    test_variables_dependant = False
    for block in reversed(tree.body):
        remove_useless_in_block(block, dependant_variables)
        if test_variables_dependant == False:
            test_variables_dependant = check_if_variables_are_dependent(block, dependant_variables)

    for block in reversed(tree.orelse):
        remove_useless_in_block(block, dependant_variables)
        if test_variables_dependant == False:
            test_variables_dependant = check_if_variables_are_dependent(block, dependant_variables)

    if test_variables_dependant:
        #need to add the test variables to dependant_variables list
        remove_useless_in_block(tree.test,dependant_variables)
'''
Function to handle the case of ast.Assign object
'''
def remove_useless_assign(tree, dependant_variables):
    if check_if_subtree_has_named_expr(tree) and check_if_variables_are_dependent(tree, dependant_variables):
        for target in tree.targets:
            add_value_to_dependent_variable(dependant_variables, get_target_name_for_assignment(target))

    elif isinstance(tree.value, ast.Call):
        function_name = tree.value.func.value.id
        if not check_if_function_pure(function_name):
            add_value_to_dependent_variable(dependant_variables, tree.targets[0].id)

    else:
        for target in tree.targets:
            target_id = get_target_name_for_assignment(target)
            if target_id in dependant_variables:
                get_dependent_variables(dependant_variables,tree.value)

'''
Recursively calls all the statements within the compare statement
'''
def remove_useless_compare(tree, dependant_variables): 
    get_dependent_variables(dependant_variables, tree.left) 

    for comparator in tree.comparators:
        get_dependent_variables(dependant_variables, comparator)    


'''
The function that recursively optimizes code block by block. This is where the
mark and sweep function is implemented. The recursive call marks all the dependent
variables and the NodeTransformer does the sweep of all the not marked nodes
'''
def remove_useless_in_block(tree, dependent_variables):
    if (isinstance(tree, ast.Expr)):
        remove_useless_in_block(tree.value, dependent_variables)

    elif (isinstance(tree,ast.Call)):
        remove_useless_function_call(tree, dependent_variables)

    elif (isinstance(tree,ast.FunctionDef)):
        remove_useless_function_definition(tree, dependent_variables)

    elif(isinstance(tree,ast.For)):
        remove_useless_for(tree, dependent_variables)

    elif(isinstance(tree,ast.While)):
        remove_useless_while(tree, dependent_variables)

    elif (isinstance(tree,ast.Return)):
        get_dependent_variables(dependent_variables, tree.value)
    
    elif (isinstance(tree,ast.If)):
        remove_useless_if(tree, dependent_variables)

    elif (isinstance(tree, ast.Assign)):
        remove_useless_assign(tree, dependent_variables)
                    
    elif isinstance(tree,ast.NamedExpr):
        if tree.target.id in dependent_variables:
            get_dependent_variables(dependent_variables,tree.value)

    elif isinstance(tree,ast.AugAssign):
        if tree.target.id in dependent_variables:
            get_dependent_variables(dependent_variables,tree.value)

    elif isinstance(tree,ast.Constant):
        pass

    elif isinstance(tree,ast.Compare):
        remove_useless_compare(tree, dependent_variables)

    elif isinstance(tree,ast.Name):
        get_dependent_variables(dependent_variables,tree)

    elif isinstance(tree,ast.Module):
        for block in reversed(tree.body):
            remove_useless_in_block(block,dependent_variables)

    elif isinstance(tree, ast.ListComp):
        remove_useless_in_block(tree.elt, dependent_variables)

    else:
        pass
    
    transformer = Transformer(dependent_variables, TRANSFORMER_DEPENDENT_VARIABLES)
    transformer.visit(tree)


'''
returns the target name of the node.
'''
def get_target_name_for_assignment(node):
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Subscript):
        return node.value.id
    else:
        return ""


'''
Returns a unaryOp node object
'''
def get_unary_op_node():
    t = ast_parse("""
        not a 
        """)
    generator = ast.walk(t)
    for every_node in generator:
        if isinstance(every_node, ast.UnaryOp):
            return every_node

'''
Checks for consistency in if-else node of AST. If there are no statements in the 
else block, removes the 
'''
def check_new_ast_for_consistency(new_tree):
    pass_node = ast.Pass()
    unary_op_node = ast.UnaryOp()

    #Checking if the transformed tree has any function def
    #with no statements in it. This would throw an error in
    #and hence, we need to add pass statement to this function definition
    generator = ast.walk(new_tree)
    for node in generator:
        if isinstance(node,ast.FunctionDef):
            if len(node.body) == 0:
                node.body.append(pass_node)

        if isinstance(node,ast.Try):
            if len(node.body) == 0:
                node.body.append(pass_node)
                #Since we append for body of try and we see that there are no
                #statements, we then have to remove all statements in all
                #except handlers for this
                for handler in node.handlers:
                    for i in range(0,len(handler.body)):
                        handler.body.pop(0)
                    handler.body.append(pass_node)

        elif isinstance(node,ast.If):
            for every_node in node.body:
                check_new_ast_for_consistency(every_node)
            
            for every_node in node.orelse:
                check_new_ast_for_consistency(every_node)

            #If the body is empty, we replace the test condition with
            #not test condition and add all statements from orelse list
            # to body list and clear the orelse list at the end 
            if len(node.body) == 0:
                #Negating the condition
                unary_op_node = get_unary_op_node()
                unary_op_node.operand = node.test
                node.test = unary_op_node

                #Adding all statements in if block
                for every_statement in node.orelse:
                    node.body.append(every_statement)
                
                #Clearing if block
                node.orelse.clear()

    

'''
Checks for pass statements in AST. If found, removes all the subsequent
statements in the parent block
'''
def check_new_ast_for_pass(new_tree):
    t = Transformer([], TRANSFORMER_DO_NOTHING)
    t.visit(new_tree)
    queue = []
    queue.append(new_tree)        

    #We do a BFS on the AST and when we detect a pass, we delete all the
    #subsequent nodes
    while queue:
        parent_node = queue.pop(0)
        if "body" in parent_node._fields: 
            length_of_parent_node = len(parent_node.body)

            pass_found_at = -1
            pass_found = False
            delete_nodes = []

            for iterator in range(length_of_parent_node):

                if pass_found==False:
                    if isinstance(parent_node.body[iterator],ast.Pass):
                        pass_found = True
                        pass_found_at = iterator
                        break
                    else:
                        queue.append(parent_node.body[iterator])
              
        #We found pass at the pass_found. Need to remove all the statements that
        #come after this. If not found, do nothing
            if pass_found:
                length_of_list = len(parent_node.body)
                number_of_deletions = length_of_list - pass_found_at - 1
                for i in range (0,number_of_deletions):
                    del parent_node.body[pass_found_at+1]
    return

'''
Checks for empty for statements in AST. If found, removes these from the AST
'''
def check_new_ast_empty_for(tree):
    t = Transformer([], TRANSFORMER_DO_NOTHING)
    t.visit(tree)
    queue = []
    queue.append(tree)        
    #We do a BFS on the AST and when we detect a for and if that for has body of 0,
    #we delete the for
    while queue:
        parent_node = queue.pop(0)
        if "body" in parent_node._fields:
            #Add all children nodes of parent_node to list
            for block in parent_node.body:
                queue.append(block) 

            length_of_parent_node = len(parent_node.body)

            for_found_at = []
            for_found = False
            #Find all for statements that have 0 statements in the body
            #We need to remove such for statements
            for iterator in range(length_of_parent_node):
                if isinstance(parent_node.body[iterator], ast.For):
                    for_node = parent_node.body[iterator]
                    if len(for_node.body) == 0:
                        for_found_at.append(iterator)
            
            dynamic_adjust = 0
            for for_position in for_found_at:
                parent_node.body.pop(for_position - dynamic_adjust)
                dynamic_adjust = dynamic_adjust + 1
    return
  
