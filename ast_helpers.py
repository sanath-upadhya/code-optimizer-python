import ast

def clean(s):
    """Removes extra whitespace, including empty lines"""
    import inspect
    return "\n".join([s for s in inspect.cleandoc(s).splitlines() if s]) + "\n"

def ast_unparse(t):
    """AST -> code, deleting extra whitespace"""
    return "\n".join([s for s in ast.unparse(t).splitlines() if s]) + "\n"

def ast_parse(s):
    """Removes extra whitespace and parses"""
    return ast.parse(clean(s))