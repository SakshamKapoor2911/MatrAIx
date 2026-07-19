# GPU usage — Amazon 100K persona extraction (reference run)

Charged hours from the batch scheduler's accounting records. Allocation fully spent.

| GPU | Precision / parallelism | Charged GPU-hours |
|---|---|---:|
| NVIDIA H100 80GB (HBM3) | FP8, TP=1 (1 model / GPU) | **645.6** |
| NVIDIA A100 40GB (SXM4) | BF16, TP=4 (1 model / 4-GPU node) | **1,037.7** |

The A100 figure is 257.1 node-hours × 4 GPUs/node (GPU nodes are charged whole).

The two lines are separate allocations on different hardware; they are reported separately
and not summed.

Model `Qwen/Qwen3.6-35B-A3B` on vLLM ≥ 0.24.0, greedy (temp=0).
Output: **38,219 unique users** (38.2% of the 100K target).
