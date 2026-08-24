#!/usr/bin/env python3
"""Finite falsifier for the line-graph premise in Frank Vega's 2XHS route.

Claim under test (paper Theorem 6, as read from the public preprint):
legal 2XHS instances induce line graphs, so maximum independent set can be
solved through matching.

This probe constructs K3,3 as a legal 2XHS graph and verifies an induced claw,
which is impossible in a line graph.

Finite mechanics only.  The route refutation itself is the elementary graph
argument encoded below, not a P-vs-NP conclusion.
"""

from itertools import combinations

LEFT = (0, 1, 2)
RIGHT = (3, 4, 5)
U = LEFT + RIGHT
C = tuple((u, v) for u in LEFT for v in RIGHT)


def degree(u):
    return sum(u in edge for edge in C)


def edge_intersection_size(e1, e2):
    return len(set(e1) & set(e2))


def adjacent(u, v):
    return (u, v) in C or (v, u) in C


def induced_claw():
    # center 0, leaves 3,4,5
    center = 0
    leaves = RIGHT
    assert all(adjacent(center, leaf) for leaf in leaves)
    assert all(not adjacent(a, b) for a, b in combinations(leaves, 2))
    return center, leaves


def self_test():
    # Vega Definition-2 style legality.
    assert all(degree(u) == 3 for u in U)
    assert all(
        edge_intersection_size(e1, e2) <= 1
        for e1, e2 in combinations(C, 2)
    )
    assert len(C) == 9

    center, leaves = induced_claw()

    # Elementary fact: line graphs are claw-free.  A line-graph vertex
    # corresponds to one root edge uv; all its neighbors split into the clique
    # of edges incident with u and the clique of edges incident with v, so it
    # cannot have three pairwise nonadjacent neighbors.
    print("EXT_VEGA_2XHS_K33_LEGAL = PASS")
    print("EXT_VEGA_K33_INDUCED_CLAW = PASS")
    print(f"claw_center = {center}")
    print(f"claw_leaves = {leaves}")
    print("EXT_VEGA_THEOREM6_ALL_2XHS_ARE_LINE_GRAPHS = REFUTED_BY_K33")
    print("claim_ceiling = this refutes the cited route only; P_VS_NP remains OPEN")


if __name__ == "__main__":
    self_test()
