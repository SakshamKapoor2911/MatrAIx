# Persona Graph Grounding Sources

This document collects real-world data sources used for grounding the Persona
Full DAG. It is intended as a lightweight reference for source review,
documentation, and follow-up validation.

## Dimension Reference Map

| MatrAIx dimension area | Real-world grounding target | Reference sources |
| --- | --- | --- |
| Region / population distribution | Global and regional population shares | UN World Population Prospects; UN Population Division Data Portal; World Bank World Development Indicators; WorldPop; Eurostat |
| Age | Age distributions by country, region, and population segment | UN World Population Prospects; UN Population Division Data Portal; World Bank World Development Indicators; ACS PUMS; IPUMS International; IPUMS USA |
| Sex / gender | Population shares and survey demographics | UN World Population Prospects; World Bank World Development Indicators; ACS PUMS; IPUMS International; IPUMS USA; Pew Research Center datasets |
| Urbanicity | Urban/rural population distribution | World Bank World Development Indicators; UN World Urbanization Prospects; ACS data; WorldPop |
| Education | Educational attainment and education-system indicators | UNESCO Institute for Statistics; World Bank Education Statistics; ILOSTAT; OECD Education at a Glance; OECD PISA; ACS PUMS; IPUMS International; IPUMS USA |
| Employment / occupation / work | Employment status, occupation, wages, skills, work context | ILOSTAT; BLS OEWS; O*NET; OECD employment data; ACS PUMS; IPUMS USA; IPUMS CPS |
| Income / socioeconomic status | Income, poverty, inequality, and socioeconomic priors | World Bank Poverty and Inequality Platform; World Bank WDI; World Inequality Database; Luxembourg Income Study; OECD Income Distribution Database; ACS PUMS; IPUMS USA; IPUMS CPS |
| Household / family / marital status | Household size, family structure, marital and parental status | ACS PUMS; IPUMS International; IPUMS USA; UN Population Division; OECD Family Database; DHS Program; UNICEF MICS |
| Religion / religiosity | Religious affiliation, denomination, belief, and religiosity | Pew Research Center Religion; World Values Survey; General Social Survey; ARDA |
| Values / politics / trust / social attitudes | Political lean, trust, social values, public opinion | World Values Survey; General Social Survey; Pew Research Center; European Social Survey; International Social Survey Programme; Gallup World Poll; Afrobarometer; Arab Barometer; Asian Barometer; Latinobarometro; Eurobarometer |
| Personality / psychometrics | Personality traits, psychological scales, and self-report constructs | IPIP; SAPA Project; MIDUS |
| Health / disability / accessibility | Disability, health status, accessibility needs, assistive technology | WHO Global Health Observatory; IHME Global Burden of Disease; ACS PUMS; CDC NHIS; CDC BRFSS; DHS Program; UNICEF MICS |
| Lifestyle / time use / consumption | Time use, household spending, daily activity, and lifestyle priors | American Time Use Survey; Consumer Expenditure Surveys; OECD Time Use Database |
| Technology / internet access / digital behavior | Internet access, digital adoption, technical familiarity | ITU statistics; World Bank WDI; DataReportal; Pew Internet & Technology; Stack Overflow Survey |
| Developer / coding / technical tools | Developer skills, programming languages, tools, AI-tool usage | Stack Overflow Survey; GitHub Octoverse; JetBrains State of Developer Ecosystem Report |
| Migration / citizenship / country of birth | Citizenship, migration, country of birth, remittance context | UN International Migrant Stock; OECD migration data; ACS PUMS; IPUMS International; IPUMS USA; World Bank Migration & Labor Mobility; World Bank Remittances / KNOMAD |

## Source Catalog

### Population And Demographics

- UN World Population Prospects: https://population.un.org/wpp/
- UN Population Division Data Portal: https://population.un.org/dataportal/
- UN World Urbanization Prospects: https://population.un.org/wup/
- World Bank World Development Indicators: https://databank.worldbank.org/source/world-development-indicators
- World Bank DataBank: https://databank.worldbank.org/
- WorldPop: https://www.worldpop.org/
- Eurostat: https://ec.europa.eu/eurostat
- U.S. Census ACS PUMS: https://www.census.gov/programs-surveys/acs/microdata.html
- ACS data portal: https://www.census.gov/programs-surveys/acs/data.html
- IPUMS: https://www.ipums.org/
- IPUMS International: https://international.ipums.org/international/
- IPUMS USA: https://usa.ipums.org/usa/

### Education, Work, And Socioeconomics

- UNESCO Institute for Statistics: https://uis.unesco.org/
- World Bank Education Statistics: https://databank.worldbank.org/source/education-statistics
- ILOSTAT data: https://ilostat.ilo.org/data/
- ILOSTAT explorer: https://rplumber.ilo.org/dataexplorer/?lang=en
- BLS Occupational Employment and Wage Statistics: https://www.bls.gov/oes/
- OEWS data overview: https://www.bls.gov/oes/tables.htm
- O*NET Resource Center: https://www.onetcenter.org/
- O*NET database releases: https://www.onetcenter.org/database.html
- OECD employment data: https://www.oecd.org/employment/
- OECD Education at a Glance: https://www.oecd.org/education/education-at-a-glance/
- OECD PISA: https://www.oecd.org/pisa/
- OECD Income Distribution Database: https://www.oecd.org/social/income-distribution-database.htm
- World Bank Poverty and Inequality Platform: https://pip.worldbank.org/
- World Inequality Database: https://wid.world/
- Luxembourg Income Study: https://www.lisdatacenter.org/
- IPUMS CPS: https://cps.ipums.org/cps/

### Household, Family, And Migration

- OECD Family Database: https://www.oecd.org/els/family/database.htm
- DHS Program: https://dhsprogram.com/
- UNICEF Multiple Indicator Cluster Surveys: https://mics.unicef.org/
- UN International Migrant Stock: https://www.un.org/development/desa/pd/content/international-migrant-stock
- OECD migration data: https://www.oecd.org/migration/
- World Bank Migration & Labor Mobility: https://www.worldbank.org/ext/en/topic/social-protection/migration
- World Bank Remittances / KNOMAD: https://www.worldbank.org/en/topic/migration/brief/remittances-knomad
- IPUMS International: https://international.ipums.org/international/

### Religion, Values, Politics, And Social Attitudes

- Pew Research Center datasets: https://www.pewresearch.org/datasets/
- Pew Research Center Religion: https://www.pewresearch.org/religion/
- 2025 National Public Opinion Reference Survey: https://www.pewresearch.org/dataset/2025-national-public-opinion-reference-survey-npors/
- 2023-24 Religious Landscape Study: https://www.pewresearch.org/dataset/2023-24-religious-landscape-study-rls-dataset/
- World Values Survey: https://www.worldvaluessurvey.org/
- World Values Survey Wave 7 documentation: https://www.worldvaluessurvey.org/WVSDocumentationWV7.jsp
- General Social Survey: https://gss.norc.org/
- GSS data access: https://gss.norc.org/get-the-data.html
- Association of Religion Data Archives: https://www.thearda.com/
- European Social Survey: https://www.europeansocialsurvey.org/
- International Social Survey Programme: https://issp.org/
- Gallup World Poll: https://www.gallup.com/analytics/318875/global-research.aspx
- Afrobarometer: https://www.afrobarometer.org/
- Arab Barometer: https://www.arabbarometer.org/
- Asian Barometer: https://www.asianbarometer.org/
- Latinobarometro: https://www.latinobarometro.org/
- Eurobarometer: https://europa.eu/eurobarometer/

### Personality And Psychometrics

- International Personality Item Pool: https://ipip.ori.org/
- SAPA Project: https://www.sapa-project.org/
- Midlife in the United States: https://midus.wisc.edu/

### Health, Disability, And Accessibility

- WHO Global Health Observatory: https://www.who.int/data/gho
- IHME Global Burden of Disease: https://www.healthdata.org/research-analysis/gbd
- CDC National Health Interview Survey: https://www.cdc.gov/nchs/nhis/
- CDC Behavioral Risk Factor Surveillance System: https://www.cdc.gov/brfss/

### Lifestyle, Time Use, And Consumption

- American Time Use Survey: https://www.bls.gov/tus/
- Consumer Expenditure Surveys: https://www.bls.gov/cex/
- OECD Time Use Database: https://www.oecd.org/gender/data/OECD_1564_TUSupdatePortal.htm

### Technology And Developer Behavior

- International Telecommunication Union statistics: https://www.itu.int/itu-d/reports/statistics/
- DataReportal global digital reports: https://datareportal.com/
- Pew Internet & Technology: https://www.pewresearch.org/internet/
- Stack Overflow Survey: https://survey.stackoverflow.co/
- Stack Overflow Survey 2025: https://survey.stackoverflow.co/2025
- GitHub Octoverse: https://octoverse.github.com/
- JetBrains State of Developer Ecosystem Report 2025: https://devecosystem-2025.jetbrains.com/
- JetBrains State of Developer Ecosystem Report 2024: https://www.jetbrains.com/lp/devecosystem-2024/

## Source Reference Keys

These shorthand keys identify the grounding sources referenced above.

- `acs_data_portal`: U.S. Census ACS data portal
- `acs_pums_2024_1yr`: U.S. Census ACS PUMS
- `afrobarometer`: Afrobarometer
- `arab_barometer`: Arab Barometer
- `arda`: Association of Religion Data Archives
- `asian_barometer`: Asian Barometer
- `bls_oews_may2025`: BLS Occupational Employment and Wage Statistics
- `cdc_brfss`: CDC Behavioral Risk Factor Surveillance System
- `cdc_nhis`: CDC National Health Interview Survey
- `consumer_expenditure_surveys`: Consumer Expenditure Surveys
- `datareportal`: DataReportal global digital reports
- `dhs_program`: DHS Program
- `eurobarometer`: Eurobarometer
- `european_social_survey`: European Social Survey
- `eurostat`: Eurostat
- `gallup_world_poll`: Gallup World Poll
- `github_octoverse`: GitHub Octoverse
- `gss_1972_2024`: General Social Survey
- `ihme_gbd`: IHME Global Burden of Disease
- `ilostat`: ILOSTAT
- `ipip`: International Personality Item Pool
- `ipums`: IPUMS
- `ipums_cps`: IPUMS CPS
- `ipums_international`: IPUMS International
- `ipums_usa`: IPUMS USA
- `issp`: International Social Survey Programme
- `itu_statistics`: International Telecommunication Union statistics
- `jetbrains_developer_ecosystem_2025`: JetBrains State of Developer Ecosystem Report 2025
- `latinobarometro`: Latinobarometro
- `luxembourg_income_study`: Luxembourg Income Study
- `midus`: Midlife in the United States
- `onet_30_3`: O*NET 30.3
- `oecd_education_at_a_glance`: OECD Education at a Glance
- `oecd_employment`: OECD employment data
- `oecd_family_database`: OECD Family Database
- `oecd_income_distribution_database`: OECD Income Distribution Database
- `oecd_migration`: OECD migration data
- `oecd_pisa`: OECD PISA
- `oecd_time_use_database`: OECD Time Use Database
- `pew_npors_2025`: Pew 2025 National Public Opinion Reference Survey
- `pew_research_center`: Pew Research Center datasets
- `pew_religion`: Pew Research Center Religion
- `pew_technology`: Pew Internet & Technology
- `pew_rls_2023_2024`: Pew 2023-24 Religious Landscape Study
- `sapa_project`: SAPA Project
- `un_wpp_2024`: UN World Population Prospects 2024
- `un_world_urbanization_prospects`: UN World Urbanization Prospects
- `un_international_migrant_stock`: UN International Migrant Stock
- `unesco_uis`: UNESCO Institute for Statistics
- `unicef_mics`: UNICEF Multiple Indicator Cluster Surveys
- `who_gho`: WHO Global Health Observatory
- `world_bank_databank`: World Bank DataBank
- `world_bank_education_statistics`: World Bank Education Statistics
- `world_bank_migration_labor_mobility`: World Bank Migration & Labor Mobility
- `world_bank_remittances_knomad`: World Bank Remittances / KNOMAD
- `world_bank_pip`: World Bank Poverty and Inequality Platform
- `world_bank_wdi`: World Bank World Development Indicators
- `world_inequality_database`: World Inequality Database
- `worldpop`: WorldPop
- `wvs_wave7_csv_v6_0`: World Values Survey Wave 7
- `stackoverflow_survey_2025`: Stack Overflow Survey 2025
