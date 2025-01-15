class AbelianGroup:
    def __init__(self, elements, operation):
        self.elements = set(elements)
        self.operation = operation

    def check_closure(self):
        """Check if the closure property holds."""
        for a in self.elements:
            for b in self.elements:
                if self.operation(a, b) not in self.elements:
                    return False
        return True

    def check_associativity(self):
        """Check if the associativity property holds."""
        for a in self.elements:
            for b in self.elements:
                for c in self.elements:
                    if self.operation(self.operation(a, b), c) != self.operation(a, self.operation(b, c)):
                        return False
        return True

    def check_commutativity(self):
        """Check if the commutativity property holds."""
        for a in self.elements:
            for b in self.elements:
                if self.operation(a, b) != self.operation(b, a):
                    return False
        return True

    def find_identity(self):
        """Find the identity element."""
        for e in self.elements:
            if all(self.operation(e, a) == a for a in self.elements):
                return e
        return None

    def find_inverses(self):
        """Find the inverse elements."""
        inverses = {}
        identity = self.find_identity()
        if identity is None:
            return inverses
        for a in self.elements:
            for b in self.elements:
                if self.operation(a, b) == identity:
                    inverses[a] = b
                    break
        return inverses

# Example usage with integers under addition
elements = {0, 1, -1, 2, -2}
def add(a, b):
    return a + b

group = AbelianGroup(elements, add)

print("Checking Closure:", group.check_closure())
print("Checking Associativity:", group.check_associativity())
print("Checking Commutativity:", group.check_commutativity())
identity = group.find_identity()
print(f"Identity Element: {identity}")
if identity is not None:
    print("Inverses:", group.find_inverses())

# Example usage with non-zero real numbers under multiplication
elements = {1, -1, 2, -2}
def multiply(a, b):
    return a * b

group = AbelianGroup(elements, multiply)

print("\nChecking Closure:", group.check_closure())
print("Checking Associativity:", group.check_associativity())
print("Checking Commutativity:", group.check_commutativity())
identity = group.find_identity()
print(f"Identity Element: {identity}")
if identity is not None:
    print("Inverses:", group.find_inverses())