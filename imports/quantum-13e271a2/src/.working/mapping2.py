from collections.abc import Mapping
from functools import reduce

def mapper(mapping_description, input_data):
    def transform(xform, value):
        if callable(xform):
            return xform(value)
        elif isinstance(xform, Mapping):
            return {k: transform(v, value) for k, v in xform.items()}
        else:
            raise ValueError(f"Invalid transformation: {xform}")

    def get_value(key):
        if isinstance(key, str) and key.startswith(":"):
            return input_data.get(key[1:])
        return input_data.get(key)

    def process_mapping(mapping_description):
        result = {}
        for key, xform in mapping_description.items():
            if isinstance(xform, str):
                value = get_value(xform)
                result[key] = value
            elif isinstance(xform, Mapping):
                if "key" in xform:
                    value = get_value(xform["key"])
                    if "xform" in xform:
                        result[key] = transform(xform["xform"], value)
                    elif "xf" in xform:
                        if isinstance(value, list):
                            transformed = [xform["xf"](v) for v in value]
                            if "f" in xform:
                                result[key] = xform["f"](transformed)
                            else:
                                result[key] = transformed
                        else:
                            result[key] = xform["xf"](value)
                    else:
                        result[key] = value
                else:
                    result[key] = process_mapping(xform)
            else:
                result[key] = xform
        return result

    return process_mapping(mapping_description)

if __name__ == '__main__':
    # Test 1: Basic mapping
    assert mapper({"example/x": ":a"}, {"a": 5}) == {'example/x': 5}

    # Test 2: Mapping with transformation
    assert mapper({"x": {"key": ":a", "xform": lambda n: n + 1}}, {"a": 5}) == {'x': 6}

    # Test 3: List transformation
    assert mapper({"x": {"key": ":a", "xf": lambda n: n + 1}}, {"a": [5, 6, 7]}) == {'x': [6, 7, 8]}

    # Test 4: List transformation with reduction
    assert mapper({"example/a-inc-sum": {"key": ":a", "xf": lambda n: n + 1, "f": sum}}, {"a": [5, 6, 7]}) == {'example/a-inc-sum': 21}

    print("All tests passed successfully!")