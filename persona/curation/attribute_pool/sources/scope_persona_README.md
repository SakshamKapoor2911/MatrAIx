---
license: cc-by-nc-4.0
language:
- en
configs:
- config_name: scope_qa
  data_files:
  - split: train
    path: scope_structured.jsonl
---

# SCOPE Personas (Nemotron Augmentation)

This dataset contains synthetic persona profiles constructed from socio-psychological framework (SCOPE) [https://arxiv.org/pdf/2601.07110], designed to better support LLM simulation usecases in social and behavioral science. It is intended to be used alongside Nemotron-Persona [https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA]. Personas are grounded in a 141-item sociopsychological questionnaire spanning eight facets.

You can augment Nemotron Personas by UUID with the below snippet:

```python
  from datasets import load_dataset
  import duckdb

  scope = load_dataset("Salesforce/SCOPE-Persona", split="train")
  nemotron = load_dataset("nvidia/Nemotron-personas", split="train")

  scope_arrow = scope.data.table
  nemotron_arrow = nemotron.data.table

  uuid_list = [...]
  result = duckdb.query("""
      SELECT * FROM scope_arrow s
      INNER JOIN nemotron_arrow n ON s.uuid = n.uuid
      WHERE s.uuid IN (SELECT unnest(?))
  """, params=[uuid_list]).to_df()
```
## Overview

SCOPE (Sociopsychological Construct of Persona Evaluation) is a human-grounded framework for constructing and evaluating synthetic personas. It models personas as multidimensional sociopsychological profiles rather than demographic templates or narrative-only summaries. The framework includes eight facets:

1. Demographic Information
2. Sociodemographic Behavior
3. Personal Values & Motivations
4. Personality Traits (Big Five)
5. Behavioral Patterns & Preferences
6. Personal Identity & Life Narratives
7. Professional Identity & Career

These personas are designed to capture richer behavioral structure than demographic-only personas, improving alignment with human responses in social and behavioral tasks.

## Intended Use
These personas are intended for research use in user simulation, social and behavioral modeling, persona-conditioned evaluation, and fairness/bias analysis. The dataset is designed to support richer behavioral grounding than demographic-only or summary-only personas.

## Data Generation Notes

- Personas are constructed using a 141-item sociopsychological protocol spanning seven facets.
- `scope_qa` preserves the structured responses for each question and facet.
- Facet summaries will be released soon which consists of first person narration of the persona (Coming Soon)


## Ethical Considerations

This dataset contains synthetic personas and does not include personally identifiable information from real participants. Use responsibly when evaluating social or behavioral systems and when making claims about real-world populations.

## Paper
**The Need for a Socially-Grounded Persona Framework for User Simulation**
Pranav Narayanan Venkit, Yu Li, Yada Pruksachatkun, Chien-Sheng Wu
Salesforce Research
Paper: https://arxiv.org/pdf/2601.07110

## Citation

If you use this dataset, please cite:

```bibtex
@article{venkit2025scope,
  title={The Need for a Socially-Grounded Persona Framework for User Simulation},
  author={Venkit, Pranav Narayanan and Li, Yu and Pruksachatkun, Yada and Wu, Chien-Sheng},
  journal={arXiv preprint arXiv:2601.07110},
  year={2025}
}
```
We would like to acknowledge Yada Pruksachatkun for generating the Nemotron-scale dataset and for maintaining this Huggingface dataset repository.

## License
This dataset is released under CC BY-NC 4.0 License unless otherwise noted. This dataset should not also be used to develop models that compete with OpenAI and is only released for research purposes.