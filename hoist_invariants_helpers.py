import ast
from ast_helpers import *

'''
Gets all the variables in LHS of assignment statement
'''
def get_all_variables_lhs(targets):
    return_list = []
    for target in targets:
        if isinstance(target, ast.Name):
            return_list.append(target.id)
    return return_list

'''
This function does a pass (from top-down) of all the statements in the ast.For node
It keeps track of all the assignments of variables on the LHS of the equation and
also keeps track of all the variables which are in the RHS of a variable dependent
on the ast.For iterator. These two sets are useful to determine if we can hoist the
assignment statement above the ast.For node
'''
def get_all_related_variables(node, iterator):
    #This is a for node. Traverse all the statements in its body
    variables_lhs_of_assign = []
    variables_rhs_of_iter = []
    for statement in node.body:
        #Check if this is an assign statement. If yes, need to check further, else no
        if isinstance(statement, ast.Assign):
            if(check_if_iter_present(statement, iterator)):
                if(check_if_iter_present_lhs(statement, iterator)):
                    #Iterator present in LHS. Need to get all variables in RHS and add
                    #to rhs list
                    variables_in_statement = get_all_variables_in_statement(statement.value)
                    #need to get difference of 2 lists here
                    #All previously assigned statements removed from the prospective list
                    #because these can still be moved out of for loop
                    variables_in_statement = get_difference_of_list(variables_in_statement, variables_lhs_of_assign)
                    variables_rhs_of_iter = get_union_of_list(variables_in_statement, variables_rhs_of_iter)
                else:
                    #Iterator is present in RHS. Collect the LHS of the statement
                    for target in statement.targets:
                        variables_in_statement = get_all_variables_in_statement(target)
                        variables_lhs_of_assign = get_union_of_list(variables_in_statement, variables_lhs_of_assign)
            else:
                #Iter not present in statement. need to add all occurences of lhs
                #to list
                for target in statement.targets:
                    variables_in_statement = get_all_variables_in_statement(target)
                    variables_lhs_of_assign = get_union_of_list(variables_in_statement, variables_lhs_of_assign)
    
    return variables_lhs_of_assign, variables_rhs_of_iter

'''
Function returns a list with list1 - list2
'''
def get_difference_of_list(list1, list2):
    set1 = set(list1)
    set2 = set(list2)
    new_list = set1.difference(set2)
    return new_list

'''
Returns the iterator for the ast.For node object
'''
def get_iterator_for(node):
    return node.target.id

'''
Returns the ast.Assign object
'''
def get_assign_node():
    t = ast_parse("""
        x = a
        """)
    generator = ast.walk(t)
    for every_node in generator:
        if isinstance(every_node, ast.Assign):
            return every_node

'''
Checks if the iterator is present within the given node
'''
def check_if_iter_present(node, iterator):
    return_value = False
    node_generator = ast.walk(node)
    for child_node in node_generator:
        if(isinstance(child_node,ast.Name)):
            if child_node.id == iterator:
                return_value = True
                break
        elif isinstance(child_node, ast.Subscript):
            if child_node.slice.id == iterator:
                return_value = True
                break
        else:
            return_value = False
            
    return return_value

'''
info_object[0] - Node to be shifted out
info_object[1] - Position of the node in for loop
info_object[2] - Should ast.Assign be moved completely out of loop or only RHS
                 If this true, only RHS is moved out
info_object[3] - Line number in the original code. Needed to create the tmp variable
info_object[4] - Position of the node to be placed outside the for object
'''
def remember_loop_invariant_statement(invariant_statements, node, position, temporary, line_number, parent_node_position):
    info_object = []
    info_object.append(node)
    info_object.append(position)
    info_object.append(temporary)
    info_object.append(line_number)
    info_object.append(parent_node_position)

    invariant_statements.append(info_object)  

'''
Returns all the saved data in the invariant_object
'''
def get_info_invariant(invariant_object):
    return invariant_object[0], invariant_object[1], invariant_object[2], invariant_object[3], invariant_object[4]

'''
This returns all the variables that are present in the given node
'''
def get_all_variables_in_statement(statement):
    return_list = []
    node_generator = ast.walk(statement)
    for child_node in node_generator:
        if(isinstance(child_node,ast.Name)):
            return_list.append(child_node.id)
        elif isinstance(child_node, ast.Subscript):
            return_list.append(child_node.value.id)
        else:
            pass
            
    return return_list

'''
Checks if the iterator is present on the LHS of ast.Assign
'''
def check_if_iter_present_lhs(statement, iter):
    for target in statement.targets:
        if check_if_iter_present(target, iter):
            return True
    return False

'''
Returns the union of the list list1 and list2
'''
def get_union_of_list(list1, list2):
    set1 = set(list1)
    set2 = set(list2)
    new_list = list(set1.union(set2))
    return new_list

'''
Returns the intersection of the list list1 and list2
'''
def get_intersection_of_list(list1, list2):
    set1 = set(list1)
    set2 = set(list2)
    new_list = list(set1.intersection(set2))
    return new_list

def check_if_condition_var_present(target, variables_in_compare):
    for variable in variables_in_compare:
        if variable == target:
            return True
    return False

def remove_invariant_object(parent_node, invariant_object, adjust_for):
    #Removing all positions from for statements
    node_to_be_added, for_position, temporary, line_number, parent_node_position = get_info_invariant(invariant_object)
    if temporary:
        temp_variable_name = "__o_tmp_"+str(line_number)
        statement_to_be_changed = parent_node.body[parent_node_position].body[for_position - adjust_for]
        new_name_node = ast.Name()
        new_name_node.id = temp_variable_name
        statement_to_be_changed.value = new_name_node
    else:
        actual_position_for = for_position - adjust_for

        del parent_node.body[parent_node_position].body[actual_position_for]
        adjust_for = adjust_for + 1 

    return adjust_for

def add_invariant_object(parent_node, invariant_object, adjust_for):
    node_to_be_added, for_position, temporary, line_number, parent_node_position = get_info_invariant(invariant_object)
    actual_for_position = parent_node_position + adjust_for
    if temporary:
        temp_variable_name = "__o_tmp_"+str(line_number)
        new_assign_node = get_assign_node()
        new_assign_node.targets[0].id = temp_variable_name
        new_assign_node.value = node_to_be_added

        parent_node.body.insert(actual_for_position, new_assign_node)
    else:
        parent_node.body.insert(actual_for_position, node_to_be_added) 

    adjust_for = adjust_for + 1 

    return adjust_for


def check_invariant_statements_for(invariants_statements, node, iterator):
    iter = get_iterator_for(node)
    variables_rhs_of_iter = []
    variables_lhs_of_assign = []
    variables_lhs_of_assign, variables_rhs_of_iter = get_all_related_variables(node, iter)
    for i in range(len(node.body)):
        statement_in_for = node.body[i]
        iter_in_left = False
        iter_in_right = False
        line_number = statement_in_for.lineno
        if isinstance(statement_in_for, ast.Assign):
            if(check_if_iter_present(statement_in_for, iter)):
                for target in statement_in_for.targets:
                    iter_in_left = check_if_iter_present(target, iter)
                    break
                iter_in_right = check_if_iter_present(statement_in_for.value, iter)
                if iter_in_left and iter_in_right:
                    #Do nothing
                    pass
                elif iter_in_left and not iter_in_right:
                    #Need to shift the RHS to above only if value is not a single variable
                    if not isinstance(statement_in_for.value, ast.Name):
                        all_variables_rhs = get_all_variables_in_statement(statement_in_for.value)
                        if len(get_intersection_of_list(all_variables_rhs, variables_lhs_of_assign)) == 0: 
                            remember_loop_invariant_statement(invariants_statements, statement_in_for.value, i, True, line_number, iterator)
                elif not iter_in_left and iter_in_right:
                    #Do nothing
                    pass
                elif not iter_in_left and not iter_in_right:
                    all_variables_lhs = get_all_variables_lhs(statement_in_for.targets)
                    if len(get_intersection_of_list(all_variables_lhs, variables_rhs_of_iter)) == 0:
                        remember_loop_invariant_statement(invariants_statements, statement_in_for, i, False, line_number, iterator)
                        
            else:
                all_variables_lhs = get_all_variables_lhs(statement_in_for.targets)
                if len(get_intersection_of_list(all_variables_lhs, variables_rhs_of_iter)) == 0:
                    remember_loop_invariant_statement(invariants_statements, statement_in_for, i, False, line_number, iterator)  


def check_invariant_statements_while(invariants_statements, node, iterator):
    variables_in_compare = get_all_variables_in_statement(node.test)
    variables_lhs_of_assign = []
    variables_rhs_of_compare = []
    for variable in variables_in_compare:
        variables_lhs_of_assign, variables_rhs_of_compare_new = get_all_related_variables(node, variable)
        variables_rhs_of_compare = get_union_of_list(variables_rhs_of_compare_new, variables_rhs_of_compare)
    for i in range(len(node.body)):
        statement_in_while = node.body[i]
        line_number = statement_in_while.lineno
        if isinstance(statement_in_while, ast.Assign):
            target_has_condition_variable = False
            for target in statement_in_while.targets:
                print(target)
                if check_if_condition_var_present(target.id, variables_in_compare):
                    target_has_condition_variable = True
                    break
                else:
                    #Condition variables absent. So can move this statement up
                    #remember_loop_invariant_statement(invariants_statements, statement_in_while, i, False, line_number, iterator)
                    pass
            if target_has_condition_variable:
                #Check if rhs has condition variables. If yes, cant do anything, if no tmp variable
                variables_in_rhs = get_all_variables_in_statement(statement_in_while.value)
                print(variables_in_rhs)
                condition_variables_in_rhs = False
                for each_variable in variables_in_rhs:
                    if check_if_condition_var_present(each_variable, variables_in_compare):
                        condition_variables_in_rhs = True
                        break
                
                if condition_variables_in_rhs:
                    #Do nothing
                    pass
                else:
                    if not isinstance(statement_in_while.value, ast.Name):
                        all_variables_rhs = get_all_variables_in_statement(statement_in_while.value)
                        if len(get_intersection_of_list(all_variables_rhs, variables_lhs_of_assign)) == 0:
                            remember_loop_invariant_statement(invariants_statements, statement_in_while.value, i, True, line_number, iterator)
            else:
                #Need to check for all variables on RHS. If all are not present, we can move this up
                variables_in_rhs = get_all_variables_in_statement(statement_in_while.value)
                condition_variables_in_rhs = False
                for each_variable in variables_in_rhs:
                    if check_if_condition_var_present(each_variable, variables_in_compare):
                        condition_variables_in_rhs = True
                        break
                
                if condition_variables_in_rhs:
                    #Do nothing
                    pass
                else:
                    all_variables_lhs = get_all_variables_lhs(statement_in_while.targets)
                    if len(get_intersection_of_list(all_variables_lhs, variables_rhs_of_compare)) == 0:
                        remember_loop_invariant_statement(invariants_statements, statement_in_while, i, False, line_number, iterator)





