import inspect, hashlib
from typing import Callable, Any

def impossible_question(input_fn):
    """
    This generator morphs based on an input function that *claims* to
    demonstrate a separation between P and NP, e.g. a polytime factorizer.
    """
    source = inspect.getsource(input_fn)
    hash_of_source = hashlib.sha256(source.encode()).hexdigest()
    
    yield f"🧠 I am shaped by the function with SHA-256: {hash_of_source}"
    yield "🎯 Searching for a polytime factorization algorithm for semiprimes..."
    
    try:
        result = input_fn(391, 593)  # A semiprime example
        yield f"✅ Factorization result: {result}"
        if isinstance(result, tuple) and result[0] * result[1] == 391 * 593:
            yield "🚀 Claim verified structurally."
            yield "🧬 Morphology will now update around this truth."
        else:
            yield "❌ Output does not validate. Morphology collapses."
    except Exception as e:
        yield f"🔥 Error during morphogenesis: {e}"

# Example: user attempts to "solve" the impossible
def pretend_polytime_factorizer(a, b):
    # This is intentionally wrong. The idea is to supply a candidate anyway.
    return (1, a * b)  # nonsense, bad factorization

for update in impossible_question(pretend_polytime_factorizer):
    print(update)


def p_vs_np_experiment() -> Any:
    """
    Quinic P≠NP Query:
    1) Yield a request for a SAT-solver function `solver(formula: str)->bool`.
    2) When provided, hash its source, test it on tiny instances.
    3) If it passes, congratulate—otherwise, yield failure and exit.
    """
    # 1. Request the magic solver
    solver = yield "🔮 Provide a Python function 'solver(formula: str) -> bool' that solves SAT in polynomial time."
    
    # 2. Introspect & hash its code
    try:
        src = inspect.getsource(solver)
    except (OSError, TypeError):
        yield "❌ Could not read source. Make sure 'solver' is a top-level function."
        return
    
    digest = hashlib.sha256(src.encode()).hexdigest()
    yield f"🛡 Solver fingerprint: {digest}"
    
    # 3. Smoke-test on trivial SAT instances
    tests = [
        ("a or not a", True),
        ("(a or b) and (not a or c)", True),
        ("(a) and (not a)", False)
    ]
    for formula, expected in tests:
        try:
            result = solver(formula)
        except Exception as e:
            yield f"❌ Runtime error on `{formula}`: {e!r}"
            return
        
        if result is not expected:
            yield f"❌ Wrong answer for `{formula}` (got {result}, want {expected})"
            return
    
    # 4. Victory!
    yield "🏆 Congratulations! You’ve just proven P=NP in this toy universe."
# 1) Create the generator
gen = p_vs_np_experiment()

# 2) Prime it (get the first prompt)
print(next(gen))

# 3) Send your candidate solver
def my_solver(formula: str) -> bool:
    # (this one is *not* poly-time, just for illustration)
    return "not" not in formula

print(gen.send(my_solver))

# 4) Walk through the rest
for msg in gen:
    print(msg)
