from collections.abc import Mapping, Iterable
from functools import reduce
from collections.abc import Mapping, Iterable
from functools import reduce

def mapper(mapping_description, input_data):
    def transform(xform, value):
        if callable(xform):
            return xform(value)
        elif isinstance(xform, Mapping):
            return {k: transform(v, value) for k, v in xform.items()}
        else:
            raise ValueError(f"Invalid transformation: {xform}")
    def map_value(key, xform):
        # Add check to exclude strings from Iterable handling
        if isinstance(key, Iterable) and not isinstance(key, str):
            return [map_value(k, xform) for k in key]
        elif callable(xform):
            return lambda value: transform(xform, input_data.get(key, value))
        elif isinstance(xform, Mapping):
            return lambda value: transform(xform, input_data.get(key, value))
        else:
            # Handle string keys that start with ":"
            if isinstance(key, str) and key.startswith(":"):
                return input_data.get(key[1:])
            return input_data.get(key)
    def process_mapping(mapping_description, input_data, path=()):
        result = {}
        for key, xform in mapping_description.items():
            mapped_value = map_value(xform, input_data.get(key))
            if isinstance(xform, Mapping) and "transduce" in xform:
                transducer = xform["transduce"]
                if "xf" in transducer:
                    transformer = transform(transducer["xf"], mapped_value)
                    result[key] = reduce(transducer["f"], transformer) if transformer else None
            elif isinstance(xform, Mapping):
                if isinstance(key, Iterable) and not isinstance(key, str):  # Handle nested keys
                    for k, v in zip(key, xform.items()):
                        result[k] = process_mapping(v, input_data, path + (k,))
                else:
                    result[key] = process_mapping(xform, input_data, path + (key,))
            else:
                if isinstance(key, Iterable) and not isinstance(key, str):  # Handle nested keys
                    value = [input_data.get(k) for k in key]
                else:
                    value = input_data.get(key)
                result[key] = mapped_value
        return result
    return process_mapping(mapping_description, input_data)

if __name__ == '__main__':
    # Basic usage: Map the value of `:a` to `:x`.
    assert mapper({"example/x": ":a"}, {"a": 5}) == {'example/x': 5}

    # With transformation: Increment the value of `:a` before mapping it to `:x`.
    assert mapper({"x": {"key": ":a", "xform": lambda n: n + 1}}, {"a": 5}) == {'x': 6}

    # Transform a collection: Increment each value in the `:a` list before mapping it to `:x`.
    assert mapper({"x": {"key": ":a", "xf": lambda n: n + 1}}, {"a": [5, 6, 7]}) == {'x': [6, 7, 8]}

    # Transduce a collection: Calculate the sum of incremented values in the `:a` list and map it to
    assert mapper({"example/a-inc-sum": {"key": ":a", "xf": lambda n: n + 1, "f": sum}}, {"a": [5, 6, 7]}) == {'example/a-inc-sum': 24}