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

def test_assign_no_return():
    t = ast_parse("""
        def foo(x):
            a = 10
            b = 0
        print(foo())
        """)

    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        def foo(x):
            pass
        print(foo())
        """)

def test_assign_return():
    t = ast_parse("""
        def foo():
            a = 10
            b = 0
            c = 1
            return 5 + a
        print(foo())
        """)

    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        def foo():
            a = 10
            return 5 + a
        print(foo())
        """)

def test_assign_namedexpr_useful():
    t = ast_parse("""
        def foo():
            y = (x := 10)
            return x
        print(foo())
        """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        def foo():
            y = (x := 10)
            return x
        print(foo())
        """)

def test_assign_namedexpr_useless():
    t = ast_parse("""
        def foo():
            x = 10
            y = (z := 10)
            return x
        print(foo())
        """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        def foo():
            x = 10
            return x
        print(foo())
        """)

def test_assign_impure_function():
    t = ast_parse("""
        import sys
        x = sys.exit(0)
        """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        import sys
        x = sys.exit(0)
        """)

def test_expr():
    t = ast_parse("""
        def foo():
            x = 0
            x+1+1
            return 1
        print(foo())
        """)

    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        def foo():
            return 1
        print(foo())
        """)

def test_expr_namedexpr_useful():
    t = ast_parse("""
        def foo():
            (x := 10)
            return x
        print(foo())
        """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        def foo():
            (x := 10)
            return x
        print(foo())
        """)

def test_expr_function_call_pure():
    t = ast_parse("""
        def foo():
            x = [42]
            len(x)
            return 1
        print(foo())
        """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        def foo():
            return 1
        print(foo())
        """)

def test_expr_comprehension_impure_function():
    t = ast_parse("""
        def foo(x):
            print(x)
        [foo(x) for x in [1, 2, 3]]
        """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        def foo(x):
            print(x)
        [foo(x) for x in [1, 2, 3]]
        """)


def test_assign_in_for_after_use():
    t = ast_parse("""
        def foo(a):
            x = y = 0
            for i in range(len(a)):
                a[i] = x + y
                x = 10
                y = 12
        arr = [0, 1]
        foo(arr)
        """)

#    print(ast.dump(t, indent=4))
    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        def foo(a):
            x = y = 0
            for i in range(len(a)):
                a[i] = x + y
                x = 10
                y = 12
        arr = [0, 1]
        foo(arr)
        """)

def test_pass():
    # This is (arguably incorrect and) as discussed with Emery.
    t = ast_parse("""
        def foo():
            pass
            while True:
                pass
            for i in range(10):
                pass
            pass
            x = 10
            pass
        foo()
        """)

    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        def foo():
            pass
        foo()
        """)

def test_if_useless_else_useful():
    t = ast_parse("""
        def foo():
            a = 10
            if a:
                c = 1
            else:
                b = 2
            c = b + 10
            return b
        print(foo())
        """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)
    print(ast.dump(t, indent=4))

    assert ast_unparse(t) == clean("""
        def foo():
            a = 10
            if not a:
                b = 2
            return b
        print(foo())
        """)

def test_if_useful_else_useless():
    t = ast_parse("""
        def foo():
            a = 10
            if a:
                b = 1
            else:
                c = 100
            c = b + 10
            return b
        print(foo())
        """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)
    print(ast.dump(t, indent=4))

    assert ast_unparse(t) == clean("""
        def foo():
            a = 10
            if a:
                b = 1
            return b
        print(foo())
        """)

def test_while_namedexpr_useful():
    t = ast_parse("""
        def foo():
            a = 10
            b = 0
            c = 1
            while (z := (a + b)) < 2:
                c -= 1
                a -= 1
            return z
        print(foo())
        """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)
    print(ast.dump(t, indent=4))

    assert ast_unparse(t) == clean("""
        def foo():
            a = 10
            b = 0
            while (z := (a + b)) < 2:
                a -= 1
            return z
        print(foo())
        """)

def test_global_defined_after_use():
    t = ast_parse("""
        def func():
            global x
            x += 20
            print(x)
        x = 10
        func()
    """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        def func():
            global x
            x += 20
            print(x)
        x = 10
        func()
    """)

def test_read_nonlocal_defined_after():
    t = ast_parse("""
        def foo():
            def bar():
                return x + 2
            x = 5
            return bar()
        print(foo())
        """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        def foo():
            def bar():
                return x + 2
            x = 5
            return bar()
        print(foo())
        """)

def test_module_level_code():
    t = ast_parse("""
        x = 10
        a = x + 20
        print(x)
    """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        x = 10
        print(x)
    """)

def test_try_body_finally_useless_else_useful():
    t = ast_parse("""
        def foo():
            try:
                a = 0
            except TypeError:
                x = 1  # can't run once body is empty
            else:
                x = 2
            finally:
                c = 5
            return x
        print(foo())
    """)

    print(ast.dump(t, indent=4))
    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        def foo():
            try:
                pass
            except TypeError:
                pass
            else:
                x = 2
            return x
        print(foo())
    """)

def test_nonlocal_return_namedexpr():
    t = ast_parse("""
        def foo():
            b = 2
            def bar():
                nonlocal a, b
                return (a := b)
            a = 10
            bar()
            return a
        print(foo())
        """)

    t = remove_useless(t)

    assert ast_unparse(t) == clean("""
        def foo():
            b = 2
            def bar():
                nonlocal a, b
                return (a := b)
            a = 10
            bar()
            return a
        print(foo())
        """)

# --- hoist tests

def test_hoist_example():
    t = ast_parse("""
        def foo(a, x, y):
            for i in range(len(a)):
                a[i] = x + y
        """)

    t = hoist_invariants(t)

    assert ast_unparse(t) == clean("""
        def foo(a, x, y):
            __o_tmp_3 = x + y
            for i in range(len(a)):
                a[i] = __o_tmp_3
        """)

def test_hoist_stmt():
    t = ast_parse("""
        def foo(a, x, y):
            for i in range(len(a)):
                v = 12
                a[i] = v
        """)

    t = hoist_invariants(t)

    assert ast_unparse(t) == clean("""
        def foo(a, x, y):
            v = 12
            for i in range(len(a)):
                a[i] = v
        """)

def test_hoist_stmt2():
    t = ast_parse("""
        def foo(x):
            for i in range(10):
                z = i
                y = 10 + x
            return y
        print(foo(42))
        """)

    t = hoist_invariants(t)

    assert ast_unparse(t) == clean("""
        def foo(x):
            y = 10 + x
            for i in range(10):
                z = i
            return y
        print(foo(42))
        """)


def test_cant_hoist_assignment_after_use():
    t = ast_parse("""
        def foo(a, x, y):
            v = 12
            for i in range(len(a)):
                a[i] = v
                v = 5
            return v
        """)

    t = hoist_invariants(t)

    assert ast_unparse(t) == clean("""
        def foo(a, x, y):
            v = 12
            for i in range(len(a)):
                a[i] = v
                v = 5
            return v
        """)

# --- optimize tests

def test_hoist_then_remove():
    t = ast_parse("""
        def foo(x):
            for i in range(10):
                y = 10 + x
                z = i
            return y
        print(foo(42))
        """)

    t = optimize(t)

    assert ast_unparse(t) == clean("""
        def foo(x):
            y = 10 + x
            return y
        print(foo(42))
        """)

def test_remove_hoist_remove():
    t = ast_parse("""
        def foo(x):
            y = 0
            for i in range(10):
                z = y
                y = 10 + x
            return y
        print(foo(42))
        """)

    t = optimize(t)
    assert not any(isinstance(n, ast.For) for n in ast.walk(t))
