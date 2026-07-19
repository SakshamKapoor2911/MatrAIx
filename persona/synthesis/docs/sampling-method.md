# Full DAG Sampling Method

The sampler performs vectorized forward sampling over
`proposal_view.topological_order`.

Each node has:

- a base prior `P0(X_i)`;
- zero or more pairwise CPD edges `P(X_i | X_p)`;
- optional full-CPT overlays `P(X_i | X_pa)`;
- optional conditional masks for hard or soft local consistency constraints.

For target node `X_i`, candidate value `v` receives:

```text
log q_i(v) = log P0_i(v)
           + gamma_i * sum_pairwise w_e [log P_e(v | x_p) - log P0_i(v)]
           + gamma_i * sum_full_cpt w_c [log P_c(v | x_pa) - log P0_i(v)]
```

The shrinkage term is:

```text
gamma_i = 1 / max(1, sqrt(sum_j weight_j^2))
```

This keeps dense multi-parent nodes from becoming too sharp. Full CPTs can mark
`replace_pairwise_parent_edges=true`; in that case pairwise edges from those
parents to the same target are skipped to avoid double counting.

Conditional masks multiply the proposal distribution before the draw (the
implementation samples by inverse CDF on the unnormalized masked proposal,
which selects values with exactly the normalized probabilities):

- `bad_values` with `bad_value_multiplier=0` are hard guards.
- `downweight_values` are soft penalties.
- `preferred_values` with `penalize_values_outside_preferred_set=true` are
  applicability gates.

Default sampling uses `emit_only=True`, which excludes nodes where `emit:false`.
Use `--include-hidden` or `decode_row(..., include_hidden=True)` for all graph
assignments.
