# TOCH test plan

1. Parse all TOCH contracts and keep `P_VS_NP=OPEN`.
2. Compile all Python research modules.
3. Run each module self-test.
4. Run aggregate self-test.
5. Run a negative fixture that intentionally lacks discovery and nested-closure bounds and require `OPEN`.
6. Any failure is logged as infrastructure/methodology failure, never converted into a mathematical SAT/UNSAT result.
