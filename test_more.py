import pytest
from ouroboros import remove_useless, hoist_invariants, optimize
import ast
import sys

def clean(s):
    """Removes extra whitespace, including empty lines"""
    import inspect
    return "\n".join([s for s in inspect.cleandoc(s).splitlines() if s]) + "\n"

def ast_parse(s):
    """Removes extra whitespace and parses"""
    return ast.parse(clean(s))

def ast_unparse(t):
    """AST -> code, deleting extra whitespace"""
    return "\n".join([s for s in ast.unparse(t).splitlines() if s]) + "\n"

# --- remove_useless tests

def test_aug_assign_useful():
    t = ast_parse("""
        def foo():
            y = 10
            x += y
            return x
        print(foo())
        """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)
    print(ast.dump(t, indent=4))

    assert ast_unparse(t) == clean("""
        def foo():
            y = 10
            x += y
            return x
        print(foo())
        """)
    
def test_aug_assign_useless():
    t = ast_parse("""
        def foo():
            a = 10
            x += y
            return a
        print(foo())
        """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)
    print(ast.dump(t, indent=4))

    assert ast_unparse(t) == clean("""
        def foo():
            a = 10
            return a
        print(foo())
        """)
    
def test_aug_assign_hoist_useful():
    t = ast_parse("""
        def foo():
            for i in range(10):
                a[i] += 10
            return a
        print(foo())
        """)

    print(ast.dump(t, indent=4))
    t = hoist_invariants(t)
    print(ast.dump(t, indent=4))

    assert ast_unparse(t) == clean("""
        def foo():
            for i in range(10):
                a[i] += 10
            return a
        print(foo())
        """)
    
def test_hoist_var_assigned_after_use():
    t = ast_parse("""
        def foo():
            for i in range(10):
                a[i] = b + c
                b = i
            return a
        print(foo())
        """)
    
    print(ast.dump(t, indent=4))
    t = hoist_invariants(t)
    print(ast.dump(t, indent=4))

    assert ast_unparse(t) == clean("""
        def foo():
            for i in range(10):
                a[i] = b + c
                b = i
            return a
        print(foo())
        """)

def test_hoist_maintain_order():
    t = ast_parse("""
        x = y = 5
        a = []
        for i in range(10):
            z = x + (y := 10)
            a[i] = x + y
        """)

    print(ast.dump(t, indent=4))
    t = hoist_invariants(t)
    print(ast.dump(t, indent=4))


    assert ast_unparse(t) == clean("""
        x = y = 5
        a = []
        z = x + (y := 10)
        __o_tmp_5 = x + y
        for i in range(10):
            a[i] = __o_tmp_5
        """)
    
def test_hoist_nested_for():
    t = ast_parse("""
        x = y = z = 5
        a = []
        for j in range(10):
            a[j] += z 
            for i in range(10):
                z = x + (y:=10)
                a[i] = x + y
    """)

    print(ast.dump(t, indent=4))
    t = hoist_invariants(t)
    print(ast.dump(t, indent=4)) 

    assert ast_unparse(t) == clean("""
        x = y = z = 5
        a = []
        for j in range(10):
            a[j] += z
            z = x + (y := 10)
            __o_tmp_7 = x + y
            for i in range(10):
                a[i] = __o_tmp_7
    """)  

def test_hoist_nested_for_hoist_both():
    t = ast_parse("""
        x = y = z = 5
        a = []
        for j in range(10):
            a[j] = x + z 
            for i in range(10):
                z = x + (y:=10)
                a[i] = x + y
    """)

    print(ast.dump(t, indent=4))
    t = hoist_invariants(t)
    print(ast.dump(t, indent=4)) 

    assert ast_unparse(t) == clean("""
        x = y = z = 5
        a = []
        __o_tmp_4 = x + z
        for j in range(10):
            a[j] = __o_tmp_4
            z = x + (y := 10)
            __o_tmp_7 = x + y
            for i in range(10):
                a[i] = __o_tmp_7
    """) 

def test_remove_useless_nested_if():
    t = ast_parse("""
        def foo(a):
            x=10
            if (x > a):
                y = 100
                if (x < 100):
                    z =200
                else:
                    a = 200
            else:
                z = 300
            return a
        print(foo(a))
    """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)
    print(ast.dump(t, indent=4)) 

    assert ast_unparse(t) == clean("""
        def foo(a):
            x = 10
            if x > a:
                if not x < 100:
                    a = 200
            return a
        print(foo(a))
    """) 

def test_hoist_remove_nested_for():
    t = ast_parse("""
        def foo(a):
            x = y = z = 5
            for i in range(a):
                for j in range(a):
                    x = y + z
            return a
        print(foo(a))
    """)

    print(ast.dump(t, indent=4))
    t = optimize(t)
    print(ast.dump(t, indent=4)) 

    assert ast_unparse(t) == clean("""
        def foo(a):
            return a
        print(foo(a))
    """) 

def test_remove_hoist_return_constant():
    t = ast_parse("""
        def func():
            x = 10
            for i in range(10):
                y += .5
            a = x + 7 / .55
            return 42
    """)

    print(ast.dump(t, indent=4))
    t = optimize(t)
    print(ast.dump(t, indent=4)) 

    assert ast_unparse(t) == clean("""
        def func():
            return 42
    """) 

def test_hoist_while():
    t = ast_parse("""
        def func():
            while a > b:
                x = s + u
                a = a + 1
    """)

    print(ast.dump(t, indent=4))
    t = hoist_invariants(t)
    print(ast.dump(t, indent=4)) 

    assert ast_unparse(t) == clean("""
        def func():
            x = s + u
            while a > b:
                a = a + 1
    """) 

def test_hoist_while_tmp():
    t = ast_parse("""
        def func():
            while a > b:
                b = s + u
                a = a + 1
    """)

    print(ast.dump(t, indent=4))
    t = hoist_invariants(t)
    print(ast.dump(t, indent=4)) 

    assert ast_unparse(t) == clean("""
        def func():
            __o_tmp_3 = s + u
            while a > b:
                b = __o_tmp_3
                a = a + 1
    """) 

def test_hoist_while_var_used_after():
    t = ast_parse("""
        def func():
            while a > b:
                x = m + n
                a = x + 1
    """)

    print(ast.dump(t, indent=4))
    t = hoist_invariants(t)
    print(ast.dump(t, indent=4)) 

    assert ast_unparse(t) == clean("""
        def func():
            x = m + n
            while a > b:
                a = x + 1
    """) 

def test_hoist_while_var_used_before():
    t = ast_parse("""
        def func():
            while a > b:
                a = x + 1
                x = m + n
    """)

    print(ast.dump(t, indent=4))
    t = hoist_invariants(t)
    print(ast.dump(t, indent=4)) 

    assert ast_unparse(t) == clean("""
        def func():
            while a > b:
                a = x + 1
                x = m + n
    """) 

