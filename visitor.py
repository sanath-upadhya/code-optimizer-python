import ast

class Visitor(ast.NodeVisitor):
    def __init__(self):
        self.function_nodes=[]
        self.assignment_nodes = []
        self.return_nodes = []
        self.if_nodes = []

    def visit(self, node):
        super().visit(node)
        

    def visit_Return(self,node):
        self.return_nodes.append(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.function_nodes.append(node)
        self.generic_visit(node)

    def visit_Assign(self, node):
        self.assignment_nodes.append(node)
        self.generic_visit(node)

    def visit_NamedExpr(self,node):
        self.assignment_nodes.append(node)
        self.generic_visit(node)

    def visit_AugAssign(self,node):
        self.assignment_nodes.append(node)
        self.generic_visit(node)

    def visit_For(self,node):
        self.if_nodes.append(node)
        self.generic_visit(node)
