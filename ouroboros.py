import ast
import copy
import sys
from transformer import *
from visitor import *
from constant import *
from hoist_invariants_helpers import *
from ast_helpers import *
from remove_useless_helpers import *

'''
The function removes all the useless assignment statements in the given AST.
This is done by the function remove_useless_in_block() and this implements the 
mark-and-sweep algorithm

After the removal of the useless statements, it does the following:

If there are any pass statements within a block, all the statements after that
are removed (since they will never be called). The function check_new_ast_for_pass()
does this work

If there are any empty for statements in AST (i.e., if the body of for block has no
statements in it), the for_node in AST is deleted. This is done by the function
check_ast_empty_for()

Lastly, it checks for consistency of the whole AST. If there are any if statements and the
if block is empty but not the else block, it reverses the check condition. This is taken care
by the function check_new_ast_for_consistency() 
'''
def remove_useless(tree: ast.AST) -> ast.AST:
    # Implement this optimization here
    dependent_variables = [] 
    remove_useless_in_block(tree,dependent_variables)
    
    check_new_ast_for_pass(tree)
    
    check_new_ast_empty_for(tree)
    
    check_new_ast_for_consistency(tree)

    return tree


'''
This function traverses the given AST using BFS technique. During BFS, if this encounters
a ast.For/ast.While node, it does the following:

There are 2 passes over all the blocks within the node. 
In the first pass, we collect all the variables that are assigned inside the for block 
and also all the variables that cannot be shifted to the top.

In the second pass, we check if an individual statement can be hoisted upwards. If yes, we store
this information and proceed further,

At the end of the 2 passes, we look at the stored information object and do the necessary 
modifications to the ast.For/ast.While node and it's parent node

NOTE: The order of the statements put to the top of the parent node are maintained
in accordance to how they occur in the for block. Please see test_hoist_maintain_order()
for the test case and expected output.
'''
def hoist_invariants(tree: ast.AST) -> ast.AST:
    # Implement this optimization here
    queue = []
    queue.append(tree)

    while queue:
        parent_node = queue.pop(0)
        if "body" in parent_node._fields:
            length_of_parent_node = len(parent_node.body)
            
            #Add all children to list
            for block in parent_node.body:
                queue.append(block)

            invariants_statements = [] 
            #Find all for statements that have 0 statements in the body
            #We need to remove such for statements
            for iterator in range(length_of_parent_node):
                node = parent_node.body[iterator]
                if isinstance(node, ast.For):
                    check_invariant_statements_for(invariants_statements, node, iterator)   
                
                elif isinstance(node, ast.While):
                    check_invariant_statements_while(invariants_statements, node, iterator)

            adjust_for = 0
            for invariant_object in invariants_statements:
                adjust_for = remove_invariant_object(parent_node, invariant_object, adjust_for)               

            adjust_for = 0    
            for invariant_object in invariants_statements:
                adjust_for = add_invariant_object(parent_node, invariant_object, adjust_for)
                
    
    return tree


'''
This function runs the remove_useless() and hoist_invariants() continuously
until there are no changes made to the AST
'''
def optimize(tree: ast.AST) -> ast.AST:
    # Implement this optimization here
    change = True
    while change:
        original_tree = copy.deepcopy(tree)

        tree = remove_useless(tree)
        tree = hoist_invariants(tree)

        try:
            assert ast.unparse(original_tree) == ast.unparse(tree)
        except AssertionError:
            print("Tree still changing")
            change = True
        else:
            print("Tree is stable")
            change = False
    return tree


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    ap = argparse.ArgumentParser()
    ap.add_argument("script", type=Path, help="the script to transform")
    g = ap.add_mutually_exclusive_group(required=False)
    g.add_argument("--dont", action="store_true", help="don't optimize")
    g.add_argument("--hoist", action="store_true", help="hoist invariants")
    g.add_argument("--remove", action="store_true", help="remove useless")
    args = ap.parse_args()

    with open(args.script, "r") as f:
        t = ast.parse(f.read())
        
    if not args.dont:
        if args.hoist:
            t = hoist_invariants(t)
        elif args.remove:
            t = remove_useless(t)
        else:
            t = optimize(t)

    split_string = str.split(".",str(args.script))
    new_filename = split_string[0] + "_optimized.py"
    
    with open(new_filename, 'w') as sys.stdout:
        print(ast.unparse(t))

