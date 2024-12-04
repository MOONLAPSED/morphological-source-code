from math import sqrt, hypot
from numbers import Number
from collections import deque, ChainMap
from typing import List, Tuple, Union

import builtins
import os, argparse

defaults = {'permissions': 'ADMIN'}

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--permissions')
namespace = parser.parse_args()
command_line_args = {k: v for k, v in vars(namespace).items() if v is not None}

combined = ChainMap(command_line_args, os.environ, defaults)
print(combined['permissions'])
pylookup = ChainMap(locals(), globals(), vars(builtins))

a = 0b1010 #Binary Literals
b = 100 #Decimal Literal 
c = 0o310 #Octal Literal
d = 0x12c #Hexadecimal Literal
float1 = 10.5 #Float Literal
float2 = 1.5e2 #Scientific Literal
x = 3.14j #Complex Literal
Vector = tuple[Number, ...] # https://en.wikipedia.org/wiki/Coordinate_vector
queue = deque([a, b, c, d]); queue.append(float1); queue.append(float2)
for item in queue:
    print(f'{item.__float__}')
    print(item.__repr__())
print(x.__reduce_ex__(a))
print(x.__str__())
def min_max_scale(x: Number, min_x: Number, max_x: Number):
    """https://en.wikipedia.org/wiki/Feature_scaling#Rescaling_(min-max_normalization)"""
    return (x - min_x) / (max_x - min_x)
def dot_product(a: Vector, b: Vector):
    """https://en.wikipedia.org/wiki/Dot_product"""
    return sum(i * j for i, j in zip(a, b))
def cosine_similarity(a: Vector, b: Vector):
    """https://en.wikipedia.org/wiki/Cosine_similarity"""
    return dot_product(a, b) / (
        sqrt(sum(i**2 for i in a)) * sqrt(sum(i**2 for i in b))
    )
def dot_product(a: Vector, b: Vector):
    """https://en.wikipedia.org/wiki/Dot_product"""
    return sum(i * j for i, j in zip(a, b))
def average(a: Vector) -> Number:
     """https://en.wikipedia.org/wiki/Average"""
     return sum(a) / len(a)