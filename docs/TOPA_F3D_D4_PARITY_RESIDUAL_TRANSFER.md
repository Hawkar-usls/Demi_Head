# TOPA F3D-D4-X — Exact Parity Residual Transfer Under Source Self-Reduction

**Frozen:** 2026-08-24T23:05:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA`  
**Source:** Dmitry Sokolov, *Pseudorandom Generators, Resolution and Heavy Width*, CCC 2022, DOI `10.4230/LIPIcs.CCC.2022.15`.  
**Status:** `PARITY_SELF_REDUCTION_TRANSFER_PROVED_IN_STATED_SCOPE`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Scope

This theorem is specific to the JANUS parity-NW hard-family route.

Let the original NW outputs be parity constraints over neighborhoods of a bipartite dependency graph `G=(L,R,E)` with maximum left degree `Delta`.

Let `rho` be a Sokolov self-reduction. By Definition 20 / Remark 21 the residual graph is

```text
G' := G \ (L_rho union N(L_rho))
```

and the restricted functional formula is equivalent under normal assignments to the PRG formula over residual functions

```text
f'_i := f_i | rho.
```

The self-reduction guarantee gives

```text
G' is an (r, Delta, (1-2*epsilon)*Delta)-expander.
```

## 2. D4-X1 — direct parity CNF commutes exactly with restriction

For one parity constraint on variable set `V`, let

```text
DIRPARITY(V,c)
```

be its standard truth-table CNF: one clause forbids each assignment to `V` having parity different from `c`.

Let `rho` assign a subset `A subseteq V`.

### Lemma

If the constraint is not already fully satisfied/removed, then

```text
DIRPARITY(V,c) | rho
=
DIRPARITY(V\A, c xor parity(rho|A))
```

up to deletion of satisfied literals/clauses and canonical clause ordering.

### Proof

Each original forbidden assignment `alpha:V->{0,1}` has one blocking clause. If `alpha` disagrees with `rho` on an assigned variable, its clause contains a literal made true by `rho` and is deleted. The surviving clauses correspond bijectively to forbidden assignments extending `rho`. Removing the fixed literals maps them bijectively to assignments on `V\A` whose residual parity differs from `c xor parity(rho|A)`. Hence the restricted clause set is exactly the truth-table CNF of the residual parity equation. QED.

For every output in `L_rho`, the self-reduction assigns its entire neighborhood and satisfies its constraint, so that output's direct CNF disappears completely. Therefore for the whole direct encoding:

```text
DIRPRG_PARITY(G,b) | rho
=
DIRPRG_PARITY(G',b')
```

where each surviving output uses its residual parity constant `b'_i`.

This is exact object identity after canonical simplification, not merely a semantic analogy.

## 3. D4-X2 — residual parity retains enough balancedness

For an alive output `i`, singleton expansion in `G'` gives

```text
Delta_i' := |N_G'(i)| >= (1-2*epsilon)*Delta.
```

The residual function `f'_i` is parity, possibly complemented, on `Delta_i'` free variables.

Parity on `d` variables is `(1/2,d-1)`-balanced. Hence `f'_i` is in particular `(1/4,k)`-balanced for every

```text
k <= Delta_i'-1.
```

To reapply Sokolov Theorem 14 to `G'`, view the residual graph as an

```text
(r, Delta, (1-epsilon')*Delta)-expander
```

with

```text
epsilon' := 2*epsilon.
```

Theorem 14 then asks for `(1/4,3*epsilon'*Delta)`-balanced functions, i.e.

```text
(1/4,6*epsilon*Delta)-balanced.
```

A sufficient condition is

```text
(1-2*epsilon)*Delta - 1 >= 6*epsilon*Delta,
```

equivalently

```text
(1-8*epsilon)*Delta >= 1.
```

Under this explicit condition every residual parity output satisfies the theorem's balancedness hypothesis.

## 4. D4-X3 — residual functional-Resolution lower bound

Assume additionally `2*epsilon < 1` and all ordinary Theorem-14 hypotheses.

Applying Theorem 14 to `(G',f')` with parameter `epsilon'=2epsilon` yields

```text
L_rho
>= exp( Omega(
       (2*epsilon)^5 * r^2
       / ( 2^(6*(2*epsilon)*Delta) * m_rho )
     ) )
```

where `m_rho=|L(G')|`.

Absorbing the constant factor `2^5`:

```text
L_rho
>= exp( Omega(
       epsilon^5 * r^2
       / ( 2^(12*epsilon*Delta) * m_rho )
     ) ).
```

This is a genuine lower bound on the **residual full functional encoding**, not an imported lower bound from the unreduced formula.

## 5. D4-X4 — local residual B2 macros map legally

Let `e` be a proof-reachable residual B2 macro whose exact semantic support is contained in one residual neighborhood `N_G'(v)`.

The full functional encoding permits a variable for any Boolean function whose support lies inside one output neighborhood. Therefore the exact residual function computed by `e` has a corresponding local functional variable `y_g` in the target encoding.

Different residual B2 nodes computing the same local function may be identified by literal substitution. This is an existence/translation statement; D1 forbids treating exact semantic alias discovery as a free algorithmic operation.

Thus the semantic-local target required by F3 is legal in the residual source functional language.

## 6. D4-X5 — direct input size after restriction

Let `d_i'` be the residual degree of alive output `i`. Exact direct parity encoding has

```text
2^(d_i'-1)
```

clauses for that output.

Since

```text
(1-2*epsilon)*Delta <= d_i' <= Delta,
```

we obtain, ignoring only ordinary fixed/logarithmic variable-index encoding factors,

```text
m_rho * 2^((1-2*epsilon)*Delta-1)
<= clause_count(N_rho)
<= m_rho * 2^(Delta-1).
```

Also Definition 20 gives

```text
|L_rho| <= epsilon^2*r/16,
```

so

```text
m_rho >= m - epsilon^2*r/16.
```

In any frozen asymptotic regime where `m_rho=Theta(m)` and `Delta=C log n` with fixed `C,epsilon`, original and residual direct input lengths differ by at most a fixed polynomial factor because

```text
2^(2*epsilon*Delta)=n^(2*epsilon*C).
```

Therefore a proof polynomial in the original direct-input length remains polynomial in residual direct-input length, with a possibly different but still universal fixed exponent.

No such statement is made outside a regime with an explicit `N/N_rho` bound.

## 7. D4-X theorem

### Theorem D4-X-PARITY

For the parity-NW route, under a Sokolov self-reduction satisfying

```text
(1-8*epsilon)*Delta >= 1
```

and the stated Theorem-14 hypotheses:

1. restriction of the direct truth-table parity encoding is exactly the direct truth-table encoding of the residual parity PRG instance;
2. the residual functional encoding is the source object from Remark 21;
3. residual parity functions satisfy the balancedness required to reapply Theorem 14 with `epsilon'=2epsilon`;
4. every semantically local residual B2 macro is a legal local function of the residual full functional encoding;
5. the residual functional Resolution lower bound is

```text
exp(Omega(epsilon^5*r^2 / (2^(12*epsilon*Delta)*m_rho)));
```

6. in an explicit polynomial-input regime with `m_rho=Theta(m)` and `Delta=C log n`, original and residual direct input sizes are polynomially related by a universal fixed exponent.

Therefore the D4 collective residual theorem may be applied **unconditionally within this stated parity/self-reduction parameter regime**, rather than relying on an unproved direct-to-residual object analogy.

## 8. Resulting collective tradeoff

Let

```text
Lambda_rho
:= Omega(epsilon^5*r^2 / (2^(12*epsilon*Delta)*m_rho))
```

be the logarithm of the residual local-functional Resolution lower bound.

For a residual B2/ER3 proof of size `S_rho` with collective F3 parameters `(b_rho,d_rho)`, F3 gives

```text
7*(b_rho+2)^(d_rho+1)*log S_rho
>= Lambda_rho.
```

This is the exact residual collective obstruction available after source self-reduction.

If a separately frozen parameter regime gives

```text
Lambda_rho >= N_rho^eta
and
S_rho <= N_rho^c
```

for fixed `eta,c>0`, then

```text
(d_rho+1)*log(b_rho+2)
>= eta*log N_rho - O(log log N_rho).
```

## 9. What remains open

D4-X removes the residual-object mismatch for parity, but it does **not** convert the collective obstruction into a superpolynomial lower bound on original extension count `K`.

The remaining barrier is amortization/reuse:

```text
one original extension may remain proof-reachable and crossing
through many hard residual stages.
```

Repeated D4 inequalities cannot simply count that one extension repeatedly as distinct proof resources.

## 10. Claim firewall

```text
PARITY_RESIDUAL_TRANSFER_PROVED
!=
SUPERPOLYNOMIAL_ER3_EXTENSION_COUNT

RESIDUAL_LOCAL_LOWER_BOUND
!=
ORIGINAL_K_LOWER_BOUND_WITHOUT_AMORTIZATION

SEMANTIC_LOCAL_FUNCTION_EXISTS
!=
POLYTIME_SEMANTIC_CLASSIFIER

D4_X_PARITY
!=
P_VS_NP_RESOLUTION

P_VS_NP = OPEN
```
