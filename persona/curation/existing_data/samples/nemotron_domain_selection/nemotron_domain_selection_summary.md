# Nemotron Domain Test User Selection Summary

This folder contains a proposed Nemotron-only persona pool for testing six application domains:

- Movie / film
- Beauty
- Game
- Finance
- Medical / healthcare
- Ecommerce / retail

Amazon review personas and Amazon-derived outputs are not used in this selection.

## Files

- `nemotron_test_users_50_per_domain.md`: detailed 50-user list for each domain, with links to the full Nemotron persona YAML files.
- `nemotron_domain_selection_summary.md`: this short presentation summary.
- `nemotron_domain_diversity_visualization.md`: overall-diversity summary and 2D projection of the selected users.
- `nemotron_overall_diversity_projection.svg`: SVG plot used by the diversity visualization.
- `nemotron_within_domain_diversity_visualization.md`: within-domain diversity summary with one projection panel per application domain.
- `nemotron_within_domain_diversity_projection.svg`: SVG plot used by the within-domain diversity visualization.
- `nemotron_within_domain_cluster_visualization.md`: cluster-based within-domain visualization and cluster summaries.
- `nemotron_within_domain_cluster_projection.svg`: SVG plot showing clusters within each application domain.
- `nemotron_within_domain_cluster_projection_matplotlib.png`: Matplotlib-rendered within-domain cluster figure.
- `nemotron_within_domain_cluster_projection_matplotlib.pdf`: PDF export of the Matplotlib-rendered cluster figure.
- `nemotron_domain_user_characteristics.md`: qualitative summary of key user characteristics in each domain.

## Selection Goal

The goal is to pick domain-relevant test users while preserving profile diversity inside each domain. Each domain has 50 selected users, so the full set contains 300 domain-persona assignments.

## Selection Method

Personas were selected from
`persona/curation/existing_data/raw/nemotron_personas_usa/curated_personas/Nemotron_*.yaml`.

The scoring pass looked for domain evidence across:

- occupation
- professional profile
- skills
- hobbies
- career goals
- core persona text
- related persona sections

The final selection then applied diversity pressure so that the 50 users in each domain are not all the same type of profile. The diversity pass considered:

- occupation
- role type, such as practitioner, creator, hobbyist, or learner
- age band
- gender
- location

## Candidate Counts

| Domain | Scored candidates | Selected users |
|---|---:|---:|
| Movie / film | 12,263 | 50 |
| Beauty | 8,532 | 50 |
| Game | 14,304 | 50 |
| Finance | 23,028 | 50 |
| Medical / healthcare | 9,697 | 50 |
| Ecommerce / retail | 16,774 | 50 |

## How To Use

Use the detailed markdown file as the review surface. Each selected user row includes:

- the linked Nemotron persona file
- a compact profile summary
- the rationale for selecting that user for the domain
- the diversity role represented by that user

The linked YAML file is the source of truth for the full persona.

Use the diversity visualization file as a quick QA view for whether each domain's selected users cover different overall persona profiles in text-feature space.

Use the within-domain diversity visualization to inspect whether the 50 selected users inside each application domain cover multiple overall profile regions.

Use the cluster visualization to inspect the main persona groups inside each domain and the representative users for each group.

Use the Matplotlib cluster figure for paper or slide drafts, and use the domain characteristics summary to describe the main types of users represented in each application domain.
