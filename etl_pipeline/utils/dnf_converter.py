"""
Utility function for converting articulation expressions in polars dataframe
to disjunctive normal form

e.g.
((101 or (150 and 151)) and (205 or 230A))
becomes
(101 or 205) or (150 and 151 and 205) or (101 and 230A) or (150 and 151 and 230A)
represented as a 2d array
[
  [101, 205],
  [150, 151, 205],
  [101, 230A],
  [150, 151, 230A]
]
"""

from typing import Literal, TypedDict, Union
import itertools


class ArticulationExpr(TypedDict):
    conj: Literal["And", "Or"]
    items: list[Union["ArticulationExpr", int]]


def _to_dnf(node):
    """
    Recursively flattens a logic tree of arbitrary depth into a 2D matrix.
    Returns: List[List[int]] (Disjunctive Normal Form)
    """
    # base: no conjunctions
    if not isinstance(node, dict):
        return [[node]] if node is not None else []

    # extract logic & children
    conj = node.get("conj")
    children = node.get("items")
    if not children:
        return []

    # base: And/Or depth=1
    if all(isinstance(child, int) for child in children):
        if conj == "And":
            return [children]  # And(1, 2) -> [[1, 2]]
        else: 
            return [[x] for x in children]  # Or(1, 2) -> [[1], [2]]

    # recurse children to child matrices
    child_matrices = [_to_dnf(child) for child in children]

    # DNF algorithm: apply associative property on Or(1, 2, Or(3))
    if conj == "Or":
        merged_matrix = []
        for matrix in child_matrices:
            merged_matrix.extend(matrix)
        return merged_matrix

    # DNF algorithm: apply distributive property (And over Or)
    #    (A OR B) AND (C OR D)
    # => (A AND (C OR D)) OR (B AND (C OR D))
    # => (A AND C) OR (A AND D) OR (B AND C) OR (B AND D)
    elif conj == "And":
        product = itertools.product(*child_matrices)
        
        merged_matrix = []
        for combination in product:
            new_clause = []
            for clause in combination:
                new_clause.extend(clause)
            merged_matrix.append(new_clause)
            
        return merged_matrix
    
    return []


def to_dnf(expr: dict | int):
    """
    Recursively flattens a logic tree of arbitrary depth into a 2D matrix.
    Returns: List[List[int]] (Disjunctive Normal Form)
    """
    
    mat = _to_dnf(expr)
    return {
        "conj": "Or",
        "items": [{"conj": "And", "items": row} for row in mat]
    }
