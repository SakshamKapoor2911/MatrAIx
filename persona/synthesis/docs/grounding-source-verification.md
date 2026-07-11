# Persona Graph Grounding Source Verification

This document tracks verification notes for the grounding sources listed in
`grounding-sources.md`. It mirrors the `Source Catalog` sections in that file so
the source list and verification notes stay aligned.

Each section keeps the same source grouping as `grounding-sources.md`. Each row
focuses on dimension-level support while also recording a small amount of
source-level evidence.

## Status Labels

- `Verified`: The source is official or credible and supports the listed
  dimension areas.
- `Needs review`: The source appears relevant, but scope, access, or dimension
  fit needs another pass.
- `Replace`: The source is weak, broken, not official enough, or not directly
  relevant.
- `Remove`: The source should be removed from the grounding list.

## Population And Demographics

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| UN World Population Prospects | Official population estimates/projections; country or area coverage; age/sex tables; regional/global/national levels | The WPP page describes the dataset as official United Nations population estimates and projections, covering 237 countries or areas, with results at global, regional, national, subregional, and country/area levels. It also provides age-disaggregated datasets and sex-disaggregated population tables. | Verified |
| UN Population Division Data Portal | Demographic indicators; indicator and location search; population, urbanization, migration themes | The Data Portal provides interactive access to global demographic indicators by indicator and location, including Population, Urbanization, Marital Status, Fertility, and International Migration themes. | Verified |
| UN World Urbanization Prospects | Urbanization estimates/projections; urban/rural population; city and settlement context | UN World Urbanization Prospects is the UN Population Division source for urbanization estimates and projections, supporting urban/rural and settlement-context grounding. | Verified |
| World Bank World Development Indicators | Country-level indicators; regional aggregates; population/demographic/economic/technology series | The WDI DataBank includes countries and regional aggregates such as World, South Asia, North America, Sub-Saharan Africa, and Europe & Central Asia. It provides indicator series by country and time, including demographic, socioeconomic, education, and technology indicators. | Verified |
| World Bank DataBank | Official World Bank data platform; access to WDI and related databases; country/year indicator lookup | World Bank DataBank is the official platform for accessing World Bank datasets, including WDI and related country-level indicators. | Verified |
| WorldPop | Population distribution; spatial/geospatial demographic data; high-resolution population data; subnational age/sex structures | WorldPop describes itself as open spatial demographic data and research, with high-resolution population distribution datasets, spatial demographics, and subnational age/sex structures. | Verified |
| Eurostat | European population statistics; demographic indicators; official EU statistics portal | Eurostat is the official EU statistics portal. Its key indicators include Population, and it provides databases and statistical themes for European demographic data. | Verified, Europe-focused |
| U.S. Census ACS PUMS | Public-use person/household microdata; age, sex, education, work, income, household, migration variables | ACS PUMS is U.S. Census public-use microdata with person and household records, supporting U.S.-specific demographics, education, employment, income, disability, household, and migration grounding. | Verified, U.S.-focused |
| ACS data portal | ACS official data access; U.S. demographic/geographic statistics | The ACS data portal is an official U.S. Census access point for ACS tables, profiles, and demographic/geographic statistics. | Verified, U.S.-focused |
| IPUMS | Harmonized census/survey microdata platform; demographic, household, work, income, and migration variables | IPUMS is a University of Minnesota data platform for harmonized census and survey microdata, supporting demographic and socioeconomic grounding across multiple IPUMS collections. | Verified |
| IPUMS International | Cross-national census microdata; age, sex, education, household, birthplace/migration variables | IPUMS International provides harmonized census microdata across countries, supporting cross-national age, sex, education, household, and migration grounding. | Verified, account/license may be required |
| IPUMS USA | U.S. census/ACS microdata; age, sex, education, work, income, household, migration variables | IPUMS USA provides harmonized U.S. census and ACS microdata, supporting U.S.-specific demographic, socioeconomic, household, and migration grounding. | Verified, U.S.-focused |
| Ethnologue | Language speaker/community reference; language status and country context | Ethnologue can support language as a demographic/background attribute through language speaker and community context, but access may be limited and it should not be treated as a general population distribution source. | Verified, access may be limited |

## Education, Work, And Socioeconomics

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| UNESCO Institute for Statistics | Official education indicators; literacy, enrollment, attainment, education-system statistics | UNESCO UIS is an official international statistics source for education indicators, supporting education-system, literacy, enrollment, and attainment grounding. | Verified |
| World Bank Education Statistics | Country-level education indicators; enrollment, attainment, literacy, school system indicators | World Bank Education Statistics provides country-level education series, supporting enrollment, attainment, literacy, and education-system grounding. | Verified |
| ILOSTAT data | Labor force, employment, unemployment, occupation, education breakdowns; interactive indicator access | ILOSTAT provides international labor statistics and links to interactive access for labor-market and population indicators, supporting employment, occupation, education, age, and sex dimensions. | Verified |
| BLS Occupational Employment and Wage Statistics | Occupation employment; wage statistics; U.S. occupational labor market | BLS OEWS provides U.S. occupational employment and wage statistics, supporting occupation and compensation grounding. | Verified, U.S.-focused |
| OEWS data overview | OEWS tables and data products; occupation and wage data access | The OEWS data overview provides official BLS access to occupation employment and wage tables. | Verified, U.S.-focused |
| O*NET database releases | Occupation taxonomy; downloadable skill, knowledge, ability, education, tool, and work-context tables | O*NET database releases provide structured occupation, skill, knowledge, education, tool, and work-context data from the O*NET Resource Center. | Verified, U.S.-focused |
| OECD employment data | Employment and labor-market indicators; OECD and partner country coverage | OECD employment data supports labor-market validation for OECD and partner economies. | Verified, OECD-focused |
| OECD Indicators of Education Systems Programme | Internationally comparable education-system indicators; OECD and partner country comparisons | The Indicators of Education Systems programme develops and maintains internationally comparable data used to assess national education-system performance. | Verified, OECD-focused |
| OECD PISA | Student assessment; education-system indicators; student background data | OECD PISA supports education-system grounding through internationally comparable student assessment and background data. | Verified, student-focused |
| OECD Income and Wealth Distribution Database | Income and wealth distribution; inequality indicators; OECD and partner coverage | OECD Income and Wealth Distribution Database provides income, wealth, and inequality indicators for OECD and partner countries. | Verified, OECD-focused |
| World Bank Poverty and Inequality Platform | Poverty, inequality, welfare distribution; country-level socioeconomic indicators | The World Bank Poverty and Inequality Platform supports country-level poverty and inequality grounding. | Verified |
| World Inequality Database | Income inequality; wealth inequality; distributional indicators | The World Inequality Database provides inequality and distributional indicators for income and wealth grounding. | Verified |
| Luxembourg Income Study | Harmonized income microdata; income distribution; inequality research | LIS provides harmonized income microdata and distributional resources, supporting socioeconomic and income grounding. | Verified, requires registration |
| IPUMS CPS | U.S. labor-force survey microdata; employment, occupation, income variables | IPUMS CPS harmonizes Current Population Survey microdata, supporting U.S. employment, labor force, occupation, and income grounding. | Verified, U.S.-focused |

## Household, Family, And Migration

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| OECD Family Database | Family structure; household, fertility, child, and family-policy indicators | OECD Family Database supports family, household, fertility, child, and family-policy indicators. | Verified, OECD-focused |
| DHS Program | Household surveys; fertility, family, maternal/child health, household variables | DHS surveys provide household, fertility, family, and health variables across many countries. | Verified, survey-focused |
| UNICEF Multiple Indicator Cluster Surveys | Household survey indicators; children, households, education, health, living conditions | UNICEF MICS provides household survey data on children, households, education, health, family, and living conditions. | Verified, survey-focused |
| UN International Migrant Stock | International migrant stock; origin/destination country data | UN International Migrant Stock supports country-level migration stock and origin/destination grounding. | Verified |
| OECD migration data | Migration indicators; immigrant population; OECD and partner country coverage | OECD migration data supports migration, immigrant population, labor migration, and integration indicators. | Verified, OECD-focused |
| World Bank Migration & Labor Mobility | Migration and labor mobility context; migrant population and migration drivers | The World Bank Migration & Labor Mobility page describes global migration pressures, origin/transit/destination context, labor mobility, and migration-related research and results. | Verified |
| World Bank Remittances / KNOMAD | Remittance context; remittance flows; remittance-related data indicators | The World Bank Remittances / KNOMAD page describes remittance flows and links to remittance-related data indicators such as personal remittances received and paid. | Verified |
| IPUMS International | Household and family variables; birthplace, migration, citizenship-adjacent census variables | IPUMS International supports cross-national household composition, relationship, marital status, birthplace, migration, and demographic variables in census microdata. | Verified, account/license may be required |

## Religion, Values, Politics, And Social Attitudes

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| Pew Research Center datasets | Public opinion datasets; respondent demographics; politics, religion, social issues | Pew Research Center provides public opinion datasets and reports with respondent demographics, politics, religion, and social-issue coverage. | Verified |
| Pew Research Center Religion | Religious affiliation, belief, practice, denomination, demographics | Pew Research Center Religion provides public reports and datasets on religious affiliation, belief, practice, denomination, and demographics. | Verified |
| 2025 National Public Opinion Reference Survey | U.S. public opinion; demographics; politics and religion variables | Pew NPORS provides U.S. public opinion and demographic survey grounding. | Verified, U.S.-focused |
| 2023-24 Religious Landscape Study | U.S. religion, denomination, religiosity, demographic context | Pew Religious Landscape Study supports U.S. religion, denomination, religiosity, and demographic grounding. | Verified, U.S.-focused |
| World Values Survey Wave 7 documentation | Cross-national values, religion, trust, politics, social attitudes; Wave 7 survey documentation and data access | WVS Wave 7 documentation supports cross-national values, religion, trust, politics, social attitudes, and demographics. | Verified |
| General Social Survey | U.S. social attitudes, religion, politics, trust, values | GSS provides U.S. public-use survey data on social attitudes, trust, politics, religion, and values. | Verified, U.S.-focused |
| GSS data access | Official GSS data access for public-use survey files | GSS data access supports U.S. religion, values, politics, trust, and social-attitude grounding. | Verified, U.S.-focused |
| Association of Religion Data Archives | Religion datasets and documentation | ARDA aggregates religion datasets and documentation, supporting religious affiliation and religiosity grounding. | Verified |
| European Social Survey | European attitudes, values, politics, trust, demographics | ESS provides academically governed European survey data on attitudes, values, politics, trust, and demographics. | Verified, Europe-focused |
| International Social Survey Programme | Cross-national modules on politics, work, family, religion, identity, attitudes | ISSP provides repeated cross-national modules on social attitudes, politics, identity, work, family, religion, and related topics. | Verified |
| Gallup World Poll | Global public opinion, wellbeing, social indicators | Gallup World Poll supports global public opinion, wellbeing, and social indicator grounding, though access may be restricted. | Verified, restricted access |
| Afrobarometer | African public opinion surveys; democracy, governance, trust, values | Afrobarometer provides public opinion survey data across African countries on democracy, governance, trust, values, and social issues. | Verified, region-focused |
| Arab Barometer | MENA public opinion surveys; politics, society, religion, trust | Arab Barometer provides public opinion survey data across Arab countries on politics, society, religion, trust, and values. | Verified, region-focused |
| Asian Barometer | Asian public opinion and democracy survey data | Asian Barometer provides public opinion and democracy-related survey data across Asian societies. | Verified, region-focused |
| Latinobarometro | Latin American public opinion and social-attitude surveys | The GHDx catalog identifies Latinobarometro as a multinational public-opinion survey series covering Latin American countries from 1995 to the present. | Verified via GHDx catalog, region-focused |
| Eurobarometer | EU public opinion surveys; politics, trust, society, policy attitudes | Eurobarometer provides EU-focused public opinion survey data on politics, society, trust, and policy attitudes. | Verified, Europe-focused |

## Personality And Psychometrics

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| International Personality Item Pool | Public-domain personality items and scales; Big Five and related constructs | IPIP provides public-domain personality item pools and scales, supporting Big Five and related psychometric constructs. | Verified |
| Midlife in the United States | Longitudinal survey; psychosocial, personality, wellbeing, health measures | MIDUS provides longitudinal survey resources covering health, personality, wellbeing, and psychosocial constructs. | Verified, U.S.-focused |

## Health, Disability, And Accessibility

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| WHO Global Health Observatory | Global health indicators; official WHO data portal | WHO GHO provides official global health indicators and metadata, supporting health grounding. | Verified |
| IHME Global Burden of Disease | Disease burden, disability, health metrics; global/regional/national coverage | IHME GBD provides global, regional, and national health burden metrics, supporting health and disability grounding. | Verified |
| CDC National Health Interview Survey | U.S. health status, conditions, disability, healthcare access | CDC NHIS provides U.S. health survey data on health status, conditions, disability, and healthcare access. | Verified, U.S.-focused |
| CDC Behavioral Risk Factor Surveillance System | U.S. behavioral health and risk-factor survey; state-level coverage | CDC BRFSS provides U.S. state-level behavioral health and risk-factor survey data. | Verified, U.S.-focused |

## Lifestyle, Time Use, Consumption, And Culture

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| American Time Use Survey | Time-use activity categories; work, leisure, caregiving, household activities | ATUS provides U.S. time-use survey data covering daily activities, work, leisure, caregiving, and household activities. | Verified, U.S.-focused |
| Consumer Expenditure Surveys | Household spending, income, consumption categories | BLS Consumer Expenditure Surveys provide U.S. household spending, income, and consumption data. | Verified, U.S.-focused |
| OECD Time Use Database | Cross-national time-use comparison; activity patterns | OECD Time Use Database supports time-use and activity-pattern grounding across OECD and partner countries. | Verified, OECD-focused |
| FAOSTAT | Food and agriculture indicators; food supply and consumption context; country and time coverage | FAOSTAT provides international food and agriculture statistics that support food-system and consumption-context grounding. | Verified |
| UNESCO Institute for Statistics Culture | Internationally comparable cultural statistics; cultural participation and cultural-sector context | UNESCO UIS identifies culture as one of its statistical themes and provides internationally comparable cultural data and related statistical frameworks. | Verified |

## Technology And Developer Behavior

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| International Telecommunication Union statistics | ICT indicators; internet, mobile, broadband, digital access | ITU statistics provide official ICT indicators on internet, mobile, broadband, and digital access. | Verified |
| DataReportal global digital reports | Internet use, social media, mobile adoption, digital behavior reports | DataReportal provides global digital reports covering internet use, social media, mobile adoption, and digital behavior. | Verified, report-focused |
| Pew Internet & Technology | Internet access, device use, technology behavior surveys | Pew Internet & Technology provides survey reports on internet access, technology adoption, devices, and digital behavior. | Verified, U.S.-focused |
| Stack Overflow Survey | Developer languages, tools, AI, platforms, work, demographics | Stack Overflow Survey provides annual developer survey data covering languages, tools, platforms, work, AI-tool adoption, and demographics. | Verified, developer-focused |
| GitHub Octoverse | Developer ecosystem and platform trends; repository/language/AI trends | GitHub Octoverse reports on developer activity, repositories, languages, AI, and platform ecosystem trends. | Verified, platform/report-focused |
| JetBrains State of Developer Ecosystem | Developer tools, languages, AI, productivity, work, salary, demographics | JetBrains State of Developer Ecosystem provides survey-based developer ecosystem metrics, including languages, tools, AI, productivity, work, salary, and demographics. | Verified, developer-focused |

## Verification Templates

### Source-Level Verification Template

```text
Source:
Provider:
Official page:
Scope:
Data type:
Access type:
Supported dimensions:
Notes:
Status:
```

### Dimension-Level Verification Template

```text
Source:
Evidence to look for:
Observed evidence:
Status:
```
