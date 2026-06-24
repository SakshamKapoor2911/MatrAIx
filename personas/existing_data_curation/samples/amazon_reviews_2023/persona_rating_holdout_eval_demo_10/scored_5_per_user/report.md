# Amazon Persona Rating Holdout V1

## Cohorts

| Cohort | Users | Targets | Train mean | Train std | Train %5 | Validation mean | Validation %5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| harsh_low | 3 | 15 | 3.9478 | 1.3844 | 57.7% | 3.8000 | 53.3% |
| high_variance | 4 | 20 | 4.3296 | 0.8101 | 52.3% | 4.5000 | 55.0% |
| mostly_5 | 2 | 10 | 4.9859 | 0.2139 | 99.4% | 5.0000 | 100.0% |
| balanced_mixed | 1 | 5 | 4.8454 | 0.3819 | 85.1% | 5.0000 | 100.0% |

## Metrics

| Method | Micro MAE | Micro within-1 | Macro-user MAE | Macro-user within-1 |
| --- | ---: | ---: | ---: | ---: |
| always_5 | 0.5600 | 88.0% | 0.5600 | 88.0% |
| global_mean | 0.7254 | 88.0% | 0.7254 | 88.0% |
| category_mean | 0.6068 | 88.0% | 0.6068 | 88.0% |
| persona_yaml_sanitized_demo | 1.0400 | 78.0% | 1.0400 | 78.0% |

## Metrics By Cohort

### always_5

| Cohort | Targets | Scored | MAE | Within-1 |
| --- | ---: | ---: | ---: | ---: |
| harsh_low | 15 | 15 | 1.2000 | 66.7% |
| high_variance | 20 | 20 | 0.5000 | 95.0% |
| mostly_5 | 10 | 10 | 0.0000 | 100.0% |
| balanced_mixed | 5 | 5 | 0.0000 | 100.0% |

### global_mean

| Cohort | Targets | Scored | MAE | Within-1 |
| --- | ---: | ---: | ---: | ---: |
| harsh_low | 15 | 15 | 1.2306 | 66.7% |
| high_variance | 20 | 20 | 0.5459 | 95.0% |
| mostly_5 | 10 | 10 | 0.4594 | 100.0% |
| balanced_mixed | 5 | 5 | 0.4594 | 100.0% |

### category_mean

| Cohort | Targets | Scored | MAE | Within-1 |
| --- | ---: | ---: | ---: | ---: |
| harsh_low | 15 | 15 | 0.9679 | 66.7% |
| high_variance | 20 | 20 | 0.5302 | 95.0% |
| mostly_5 | 10 | 10 | 0.3436 | 100.0% |
| balanced_mixed | 5 | 5 | 0.3561 | 100.0% |

### persona_yaml_sanitized_demo

| Cohort | Targets | Scored | MAE | Within-1 |
| --- | ---: | ---: | ---: | ---: |
| harsh_low | 15 | 15 | 1.4000 | 66.7% |
| high_variance | 20 | 20 | 0.9000 | 90.0% |
| mostly_5 | 10 | 10 | 0.7000 | 90.0% |
| balanced_mixed | 5 | 5 | 1.2000 | 40.0% |

