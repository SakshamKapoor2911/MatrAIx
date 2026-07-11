# Stack Overflow Dimension Chunks

The schema-first Stack Overflow persona extraction design organizes all 1,290
authoritative dimensions into 45 conceptual chunks. Chunk sizes range from 20
to 40 dimensions, with a median of 28 dimensions.

The machine-readable chunk definitions are stored in
[`dimension_chunks.jsonl`](dimension_chunks.jsonl), with one
nested chunk JSON object per line. They are generated and validated by
[`prepare_dimension_chunks.py`](prepare_dimension_chunks.py).

## Demographics and language

1. `demographics_identity_household` - 28 dimensions
2. `demographics_life_course` - 24 dimensions
3. `languages_core_europe` - 25 dimensions
4. `languages_asia_africa` - 28 dimensions

## Expertise and professional context

5. `expertise_computing_data` - 23 dimensions
6. `expertise_health_life_sciences` - 22 dimensions
7. `expertise_law_economics_business` - 32 dimensions
8. `expertise_engineering_environment` - 28 dimensions
9. `expertise_humanities_creative_service` - 39 dimensions
10. `personality_character_strengths` - 34 dimensions
11. `learning_academic_background` - 34 dimensions
12. `industries_economy_infrastructure` - 25 dimensions
13. `industries_public_creative_services` - 25 dimensions
14. `professional_developer_context` - 23 dimensions

## Psychology, values, and communication

15. `psychology_decision_relational_state` - 20 dimensions
16. `values_personal_priorities` - 32 dimensions
17. `values_formal_constructs` - 20 dimensions
18. `worldview_institutions_change` - 30 dimensions
19. `worldview_civic_consumer_life` - 30 dimensions
20. `communication_cognitive_style` - 37 dimensions
21. `behavior_preferences_time` - 37 dimensions

## Skills and tools

22. `skills_communication_technical_management` - 33 dimensions
23. `skills_creative_practical_applied` - 31 dimensions
24. `tools_data_productivity_business` - 23 dimensions
25. `tools_software_cloud_development` - 23 dimensions
26. `tools_design_commerce_ai` - 23 dimensions

## Interests, culture, and media

27. `interests_society_technology_life` - 21 dimensions
28. `interests_arts_spiritual_outdoors_games` - 28 dimensions
29. `interests_community_craft_growth` - 29 dimensions
30. `culture_country_familiarity` - 40 dimensions
31. `lifestyle_consumption_routines` - 34 dimensions
32. `media_music_genres` - 35 dimensions
33. `media_film_genres` - 24 dimensions
34. `media_book_genres` - 22 dimensions
35. `food_cuisine_interests` - 35 dimensions
36. `sports_interests` - 40 dimensions

## Personality, health, hobbies, behavior, and development

37. `personality_big_five_facets` - 30 dimensions
38. `personality_bfi2` - 20 dimensions
39. `health_physical_fitness_lifestyle` - 29 dimensions
40. `hobbies_crafts_collecting_nature` - 25 dimensions
41. `hobbies_adventure_food_performance` - 25 dimensions
42. `behavior_habits` - 30 dimensions
43. `code_style_maintenance` - 22 dimensions
44. `programming_languages` - 33 dimensions
45. `developer_ai_tools_workflows` - 39 dimensions

## Validation summary

- Chunk count: 45
- Covered dimension IDs: 1,290
- Unique dimension IDs: 1,290
- Missing or duplicate IDs: 0
- Minimum chunk size: 20
- Median chunk size: 28
- Maximum chunk size: 40
- Categories split across multiple chunks: 13
- Chunks merging related source categories: 8
- Documented size exceptions: 6

To validate the tracked artifact from the repository root, run:

```bash
python persona/human_extraction/schema/prepare_dimension_chunks.py --check
```
