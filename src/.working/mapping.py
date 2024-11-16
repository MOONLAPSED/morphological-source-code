from collections.abc import Mapping, Iterable
from functools import reduce
def mapper(mapping_description, input_data):
    def transform(xform, value):
        if callable(xform):
            return xform(value)
        elif isinstance(xform, Mapping):
            if "xf" in xform and isinstance(value, list):
                transformed = [xform["xf"](v) for v in value]
                if "f" in xform:
                    return xform["f"](transformed)
                return transformed
            return {k: transform(v, value) for k, v in xform.items()}
        return value

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
            elif isinstance(xform, Mapping) and "key" in xform:
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
        return result

    return process_mapping(mapping_description)

if __name__ == '__main__':
    test1 = mapper(
        {"example/x": ":a"},
        {"a": 5}
    )
    assert test1 == {'example/x': 5}

    test2 = mapper(
        {"x": {"key": ":a", "xform": lambda n: n + 1}},
        {"a": 5}
    )
    assert test2 == {'x': 6}

    test3 = mapper(
        {"x": {"key": ":a", "xf": lambda n: n + 1}},
        {"a": [5, 6, 7]}
    )
    assert test3 == {'x': [6, 7, 8]}

    test4 = mapper(
        {"example/a-inc-sum": {"key": ":a", "xf": lambda n: n + 1, "f": sum}}, 
        {"a": [5, 6, 7]}
    )
    assert test4 == {'example/a-inc-sum': 21}  # Correct the expectation here, not 24

    print("All tests passed successfully!")