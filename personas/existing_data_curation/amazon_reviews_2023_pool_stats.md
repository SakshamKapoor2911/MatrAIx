# Amazon Reviews 2023 User Pool Stats

Exploration run over application-relevant categories from the 2018-2023 window.

## Categories

- `Books`: 10,606,530 kept reviews
- `Kindle_Store`: 11,510,161 kept reviews
- `Movies_and_TV`: 4,435,640 kept reviews
- `Electronics`: 26,479,442 kept reviews
- `Office_Products`: 8,808,413 kept reviews
- `Home_and_Kitchen`: 49,642,221 kept reviews
- `Clothing_Shoes_and_Jewelry`: 48,476,985 kept reviews

## Review Volume

The full Amazon Reviews 2023 dataset contains 571.54M reviews across all categories.
The selected categories account for about 262.5M full-dataset reviews, or 45.9%
of all reviews. In this run, the 2018-2023 window kept 159,959,392 reviews from
the selected categories, or 28.0% of the full dataset.

| Category | Full dataset reviews | % of all reviews | Kept 2018-2023 reviews | Kept % of all reviews |
| --- | ---: | ---: | ---: | ---: |
| `Books` | 29.5M | 5.16% | 10,606,530 | 1.86% |
| `Kindle_Store` | 25.6M | 4.48% | 11,510,161 | 2.01% |
| `Movies_and_TV` | 17.3M | 3.03% | 4,435,640 | 0.78% |
| `Electronics` | 43.9M | 7.68% | 26,479,442 | 4.63% |
| `Office_Products` | 12.8M | 2.24% | 8,808,413 | 1.54% |
| `Home_and_Kitchen` | 67.4M | 11.79% | 49,642,221 | 8.69% |
| `Clothing_Shoes_and_Jewelry` | 66.0M | 11.55% | 48,476,985 | 8.48% |
| **Total selected** | **262.5M** | **45.93%** | **159,959,392** | **27.99%** |

### 2018-2023 Volume Ranking

| Rank | Category | Kept 2018-2023 reviews |
| ---: | --- | ---: |
| 1 | `Home_and_Kitchen` | 49,642,221 |
| 2 | `Clothing_Shoes_and_Jewelry` | 48,476,985 |
| 3 | `Electronics` | 26,479,442 |
| 4 | `Kindle_Store` | 11,510,161 |
| 5 | `Books` | 10,606,530 |
| 6 | `Office_Products` | 8,808,413 |
| 7 | `Movies_and_TV` | 4,435,640 |

## Published Full-Dataset Category Ranking

This ranking uses the published Amazon Reviews 2023 category-level `#Rating`
counts over the full May 1996-Sep 2023 dataset. It is not restricted to the
2018-2023 window.

| Rank | Category | Full dataset reviews |
| ---: | --- | ---: |
| 1 | `Home_and_Kitchen` | 67.4M |
| 2 | `Clothing_Shoes_and_Jewelry` | 66.0M |
| 3 | `Unknown` | 63.8M |
| 4 | `Electronics` | 43.9M |
| 5 | `Books` | 29.5M |
| 6 | `Tools_and_Home_Improvement` | 27.0M |
| 7 | `Health_and_Household` | 25.6M |
| 8 | `Kindle_Store` | 25.6M |
| 9 | `Beauty_and_Personal_Care` | 23.9M |
| 10 | `Cell_Phones_and_Accessories` | 20.8M |
| 11 | `Automotive` | 20.0M |
| 12 | `Sports_and_Outdoors` | 19.6M |
| 13 | `Movies_and_TV` | 17.3M |
| 14 | `Pet_Supplies` | 16.8M |
| 15 | `Patio_Lawn_and_Garden` | 16.5M |
| 16 | `Toys_and_Games` | 16.3M |
| 17 | `Grocery_and_Gourmet_Food` | 14.3M |
| 18 | `Office_Products` | 12.8M |
| 19 | `Arts_Crafts_and_Sewing` | 9.0M |
| 20 | `Baby_Products` | 6.0M |
| 21 | `Industrial_and_Scientific` | 5.2M |
| 22 | `Software` | 4.9M |
| 23 | `CDs_and_Vinyl` | 4.8M |
| 24 | `Video_Games` | 4.6M |
| 25 | `Musical_Instruments` | 3.0M |
| 26 | `Amazon_Fashion` | 2.5M |
| 27 | `Appliances` | 2.1M |
| 28 | `All_Beauty` | 701.5K |
| 29 | `Handmade_Products` | 664.2K |
| 30 | `Health_and_Personal_Care` | 494.1K |
| 31 | `Gift_Cards` | 152.4K |
| 32 | `Digital_Music` | 130.4K |
| 33 | `Magazine_Subscriptions` | 71.5K |
| 34 | `Subscription_Boxes` | 16.2K |

## Pool Definitions

### Standard Pool

- 2018-2023 reviews
- >=30 reviews
- >=2 categories
- >=365 days history
- >=5000 review text characters
- verified_purchase_share >=0.7

### Stricter Pool

- 2018-2023 reviews
- >=50 reviews
- >=2 categories
- >=365 days history
- >=10000 review text characters
- verified_purchase_share >=0.7

### Stricter Pool, 2-Year Verified>=0.8

- 2018-2023 reviews
- >=50 reviews
- >=2 categories
- >=730 days history
- >=10000 review text characters
- verified_purchase_share >=0.8

### Stricter Pool, Cat>=3 Reference

- 2018-2023 reviews
- >=50 reviews
- >=3 categories
- >=730 days history
- >=10000 review text characters
- verified_purchase_share >=0.8

## Pool Summary

The user pools below are computed from the following categories only:
`Books`, `Kindle_Store`, `Movies_and_TV`, `Electronics`, `Office_Products`,
`Home_and_Kitchen`, and `Clothing_Shoes_and_Jewelry`.

The pool construction uses reviews in the 2018-2023 window only. Reviews outside
this window are excluded from review counts, category counts, history span,
review text character counts, and verified-purchase share. Average rating is
reported in candidate records but is not used for pool selection.

| Pool | Users |
| --- | ---: |
| Standard pool | 247,891 |
| Stricter pool | 64,855 |
| Stricter pool, 2-year verified>=0.8 | 57,765 |
| Stricter pool, cat>=3 reference | 55,032 |

## Generated Output Files

These generated artifacts are intentionally kept under ignored `raw/` paths and
are not committed to the repository.

- Standard pool: `raw/amazon_reviews_2023/exploration/application_large_2018_2023_min30_1y_5k_verified70/candidate_users.jsonl`
- Stricter pool: `raw/amazon_reviews_2023/exploration/application_large_2018_2023_min30_1y_5k_verified70/candidate_users_intermediate_min50_cat2_1y_10k_verified70.jsonl`
- Stricter pool, 2-year verified>=0.8: `raw/amazon_reviews_2023/exploration/application_large_2018_2023_min30_1y_5k_verified70/candidate_users_strict_min50_cat2_2y_10k_verified80.jsonl`
- Stricter cat>=3 reference: `raw/amazon_reviews_2023/exploration/application_large_2018_2023_min30_1y_5k_verified70/candidate_users_strict_min50_cat3_2y_10k_verified80.jsonl`
- Run summary: `raw/amazon_reviews_2023/exploration/application_large_2018_2023_min30_1y_5k_verified70/summary.json`
