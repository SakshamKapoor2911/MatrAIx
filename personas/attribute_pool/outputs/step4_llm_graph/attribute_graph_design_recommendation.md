# Attribute Graph Design Recommendation

## Recommended Graph Type

Use a heterogeneous weighted graph with three node types:

- `category`: the 10 top-level persona categories.
- `subcategory`: normalized/final subcategories under each category.
- `attribute`: canonical persona attributes after Step 3 deduplication.

This gives two complementary views:

- macro view: category and subcategory structure;
- micro view: attribute-to-attribute relations after LLM adjudication.

## Node Weights

`node_weight` should control node size.

For category and subcategory nodes, `node_weight` is log-scaled by the number of contained attributes.

For attribute nodes, `node_weight` combines:

- `quality_tier`;
- number of supporting sources;
- number of merged candidate rows.

`evidence_weight` is a cleaner support signal for attribute nodes. It is useful for filtering: keep only nodes above a threshold when drawing dense local graphs.

## Edge Types

Structural edges:

- `has_subcategory`: category -> subcategory.
- `contains_attribute`: subcategory -> attribute.

Semantic attribute edges:

- `duplicate_of`
- `alias_of`
- `broader_than`
- `narrower_than`
- `positively_correlated`
- `negatively_correlated`
- `inverse_pole`
- `conflicts_with`
- `related_but_distinct`

Only structural edges and conservative rule-seed edges are currently in `graph_edges_seed.csv`. LLM-adjudicated edges should be appended after reviewing `llm_pair_adjudication_prompts.jsonl`.

## Edge Weights

`edge_weight` should control edge thickness / force strength.

Recommended interpretation:

- `0.15-0.35`: weak structural membership edge.
- `0.4-0.65`: related but distinct / candidate correlation.
- `0.7-0.9`: strong semantic relation, hierarchy, inverse pole, or conflict.
- `0.95-1.0`: duplicate or alias relation.
- `>1.0`: category/subcategory aggregate structural edge, log-scaled by contained attribute count.

For LLM outputs, use:

`edge_weight = relation_base_weight * LLM_confidence * evidence_modifier`

where `evidence_modifier` can be based on source diversity and quality tier.

## Visualization Strategy

Do not try to draw all attribute-to-attribute candidate edges at once.

Recommended views:

1. Category map: category + subcategory nodes only.
2. Category-local graph: one top-level category plus its attributes and LLM-confirmed semantic edges.
3. Construct-local graph: start from one construct, such as `Risk tolerance`, then show 1-hop and 2-hop relations.
4. Conflict/inverse graph: only `inverse_pole`, `conflicts_with`, and `negatively_correlated` edges.
5. Evidence-filtered graph: only attributes with high `evidence_weight` and high edge confidence.

## Suggested Tools

- Gephi: fastest for exploring weighted GraphML.
- Cytoscape: good for filtering edge types and node attributes.
- NetworkX / pyvis: good for reproducible Python visualizations.
- Observable / D3: good for interactive web views once the schema stabilizes.
