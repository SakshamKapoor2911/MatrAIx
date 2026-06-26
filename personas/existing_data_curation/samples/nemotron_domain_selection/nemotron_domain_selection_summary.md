# Nemotron Domain Test User Selection Summary

This folder contains a proposed Nemotron-only persona pool for testing five application domains:

- Movie / film
- Beauty
- Game
- Finance
- Medical / healthcare

Amazon review personas and Amazon-derived outputs are not used in this selection.

## Files

- `nemotron_test_users_50_per_domain.md`: detailed 50-user list for each domain, with links to the full Nemotron persona YAML files.
- `nemotron_domain_selection_summary.md`: this short presentation summary.

## Selection Goal

The goal is to pick domain-relevant test users while preserving profile diversity inside each domain. Each domain has 50 selected users, so the full set contains 250 domain-persona assignments.

## Selection Method

Personas were selected from `personas/existing_data_curation/curated_personas/Nemotron_*.yaml`.

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

## How To Use

Use the detailed markdown file as the review surface. Each selected user row includes:

- the linked Nemotron persona file
- a compact profile summary
- the rationale for selecting that user for the domain
- the diversity role represented by that user

The linked YAML file is the source of truth for the full persona.
