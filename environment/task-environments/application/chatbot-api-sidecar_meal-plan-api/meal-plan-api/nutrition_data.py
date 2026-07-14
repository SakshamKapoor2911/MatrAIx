"""Food composition database and meal plan templates for the nutrition chatbot."""

from __future__ import annotations

from typing import Any

FOOD_DATABASE: list[dict[str, Any]] = [
    # Proteins
    {"id": "protein-chicken-breast", "name": "Grilled Chicken Breast", "category": "protein", "serving": "100g", "calories": 165, "protein_g": 31, "carbs_g": 0, "fat_g": 3.6, "tags": {"gluten-free", "dairy-free", "nut-free", "keto", "paleo"}},
    {"id": "protein-salmon", "name": "Baked Salmon", "category": "protein", "serving": "100g", "calories": 208, "protein_g": 22, "carbs_g": 0, "fat_g": 13, "tags": {"gluten-free", "dairy-free", "nut-free", "keto", "pescatarian"}},
    {"id": "protein-tofu", "name": "Firm Tofu", "category": "protein", "serving": "100g", "calories": 76, "protein_g": 8, "carbs_g": 1.9, "fat_g": 4.8, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "nut-free"}},
    {"id": "protein-lentils", "name": "Cooked Lentils", "category": "protein", "serving": "100g", "calories": 116, "protein_g": 9, "carbs_g": 20, "fat_g": 0.4, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "nut-free", "halal", "kosher"}},
    {"id": "protein-eggs", "name": "Scrambled Eggs", "category": "protein", "serving": "2 large", "calories": 155, "protein_g": 13, "carbs_g": 1.1, "fat_g": 11, "tags": {"gluten-free", "dairy-free", "nut-free", "keto", "paleo", "vegetarian"}},
    {"id": "protein-beef", "name": "Lean Ground Beef (90/10)", "category": "protein", "serving": "100g", "calories": 217, "protein_g": 26, "carbs_g": 0, "fat_g": 12, "tags": {"gluten-free", "dairy-free", "nut-free", "keto", "paleo"}},
    {"id": "protein-chickpeas", "name": "Cooked Chickpeas", "category": "protein", "serving": "100g", "calories": 139, "protein_g": 7.6, "carbs_g": 23, "fat_g": 2.6, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "nut-free", "halal", "kosher"}},
    # Grains
    {"id": "grain-brown-rice", "name": "Brown Rice", "category": "grain", "serving": "100g cooked", "calories": 123, "protein_g": 2.7, "carbs_g": 26, "fat_g": 1, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "nut-free", "halal", "kosher"}},
    {"id": "grain-quinoa", "name": "Quinoa", "category": "grain", "serving": "100g cooked", "calories": 120, "protein_g": 4.4, "carbs_g": 21, "fat_g": 1.9, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "nut-free", "halal", "kosher"}},
    {"id": "grain-oats", "name": "Rolled Oats", "category": "grain", "serving": "40g dry", "calories": 154, "protein_g": 5.4, "carbs_g": 27, "fat_g": 2.6, "tags": {"dairy-free", "vegan", "vegetarian", "nut-free", "halal", "kosher"}},
    {"id": "grain-whole-wheat-bread", "name": "Whole Wheat Bread", "category": "grain", "serving": "2 slices", "calories": 160, "protein_g": 6, "carbs_g": 28, "fat_g": 2, "tags": {"dairy-free", "vegan", "vegetarian", "nut-free", "halal", "kosher"}},
    # Vegetables
    {"id": "veg-broccoli", "name": "Steamed Broccoli", "category": "vegetable", "serving": "100g", "calories": 34, "protein_g": 2.8, "carbs_g": 7, "fat_g": 0.4, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "nut-free", "keto", "paleo", "halal", "kosher"}},
    {"id": "veg-spinach", "name": "Fresh Spinach", "category": "vegetable", "serving": "100g", "calories": 23, "protein_g": 2.9, "carbs_g": 3.6, "fat_g": 0.4, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "nut-free", "keto", "paleo", "halal", "kosher"}},
    {"id": "veg-sweet-potato", "name": "Baked Sweet Potato", "category": "vegetable", "serving": "100g", "calories": 90, "protein_g": 2, "carbs_g": 21, "fat_g": 0.1, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "nut-free", "paleo", "halal", "kosher"}},
    {"id": "veg-avocado", "name": "Avocado", "category": "vegetable", "serving": "100g", "calories": 160, "protein_g": 2, "carbs_g": 8.5, "fat_g": 15, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "nut-free", "keto", "paleo", "halal", "kosher"}},
    # Fruits
    {"id": "fruit-banana", "name": "Banana", "category": "fruit", "serving": "1 medium", "calories": 105, "protein_g": 1.3, "carbs_g": 27, "fat_g": 0.4, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "nut-free", "halal", "kosher"}},
    {"id": "fruit-blueberries", "name": "Blueberries", "category": "fruit", "serving": "100g", "calories": 57, "protein_g": 0.7, "carbs_g": 14, "fat_g": 0.3, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "nut-free", "keto", "paleo", "halal", "kosher"}},
    {"id": "fruit-apple", "name": "Apple", "category": "fruit", "serving": "1 medium", "calories": 95, "protein_g": 0.5, "carbs_g": 25, "fat_g": 0.3, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "nut-free", "paleo", "halal", "kosher"}},
    # Dairy & Alternatives
    {"id": "dairy-greek-yogurt", "name": "Greek Yogurt (plain)", "category": "dairy", "serving": "200g", "calories": 146, "protein_g": 20, "carbs_g": 7.9, "fat_g": 3.8, "tags": {"gluten-free", "nut-free", "keto", "vegetarian", "halal", "kosher"}},
    {"id": "dairy-almond-milk", "name": "Unsweetened Almond Milk", "category": "dairy", "serving": "240ml", "calories": 30, "protein_g": 1, "carbs_g": 1, "fat_g": 2.5, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "keto", "paleo", "halal", "kosher"}},
    # Fats & Oils
    {"id": "fat-olive-oil", "name": "Extra Virgin Olive Oil", "category": "fat", "serving": "1 tbsp", "calories": 119, "protein_g": 0, "carbs_g": 0, "fat_g": 13.5, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "nut-free", "keto", "paleo", "halal", "kosher"}},
    {"id": "fat-almonds", "name": "Raw Almonds", "category": "fat", "serving": "28g", "calories": 164, "protein_g": 6, "carbs_g": 6, "fat_g": 14, "tags": {"gluten-free", "dairy-free", "vegan", "vegetarian", "keto", "paleo", "halal", "kosher"}},
]

MEAL_PLAN_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "weight_loss_omnivore": [
        {"day": 1, "meals": [{"meal": "Breakfast", "items": [{"id": "dairy-greek-yogurt", "servings": 1}, {"id": "fruit-blueberries", "servings": 1}], "total_calories": 203, "total_protein_g": 20.7, "total_carbs_g": 21.9, "total_fat_g": 4.1}, {"meal": "Lunch", "items": [{"id": "protein-chicken-breast", "servings": 1.5}, {"id": "grain-quinoa", "servings": 1}, {"id": "veg-broccoli", "servings": 1.5}], "total_calories": 399, "total_protein_g": 52.5, "total_carbs_g": 31.5, "total_fat_g": 6.3}, {"meal": "Dinner", "items": [{"id": "protein-salmon", "servings": 1}, {"id": "veg-spinach", "servings": 2}, {"id": "fat-olive-oil", "servings": 1}], "total_calories": 383, "total_protein_g": 27.8, "total_carbs_g": 7.2, "total_fat_g": 26.9}], "daily_totals": {"calories": 985, "protein_g": 101, "carbs_g": 60.6, "fat_g": 37.3}},
        {"day": 2, "meals": [{"meal": "Breakfast", "items": [{"id": "protein-eggs", "servings": 1}, {"id": "veg-spinach", "servings": 1}], "total_calories": 178, "total_protein_g": 15.9, "total_carbs_g": 4.7, "total_fat_g": 11.4}, {"meal": "Lunch", "items": [{"id": "protein-beef", "servings": 1}, {"id": "grain-brown-rice", "servings": 1}, {"id": "veg-broccoli", "servings": 1}], "total_calories": 374, "total_protein_g": 31.5, "total_carbs_g": 33, "total_fat_g": 13.4}, {"meal": "Dinner", "items": [{"id": "protein-chicken-breast", "servings": 1}, {"id": "veg-sweet-potato", "servings": 1}, {"id": "veg-avocado", "servings": 0.5}], "total_calories": 335, "total_protein_g": 34, "total_carbs_g": 25, "total_fat_g": 11.1}], "daily_totals": {"calories": 887, "protein_g": 81.4, "carbs_g": 62.7, "fat_g": 35.9}},
    ],
    "vegan_high_protein": [
        {"day": 1, "meals": [{"meal": "Breakfast", "items": [{"id": "grain-oats", "servings": 1}, {"id": "fruit-banana", "servings": 1}, {"id": "fat-almonds", "servings": 0.5}], "total_calories": 367, "total_protein_g": 12.2, "total_carbs_g": 39, "total_fat_g": 10}, {"meal": "Lunch", "items": [{"id": "protein-tofu", "servings": 2}, {"id": "grain-quinoa", "servings": 1.5}, {"id": "veg-broccoli", "servings": 1}], "total_calories": 368, "total_protein_g": 29.5, "total_carbs_g": 37, "total_fat_g": 12.5}, {"meal": "Dinner", "items": [{"id": "protein-lentils", "servings": 1.5}, {"id": "grain-brown-rice", "servings": 1}, {"id": "veg-spinach", "servings": 2}], "total_calories": 395, "total_protein_g": 30, "total_carbs_g": 67, "total_fat_g": 1.5}], "daily_totals": {"calories": 1130, "protein_g": 71.7, "carbs_g": 143, "fat_g": 24}},
    ],
    "keto_standard": [
        {"day": 1, "meals": [{"meal": "Breakfast", "items": [{"id": "protein-eggs", "servings": 2}, {"id": "veg-spinach", "servings": 1}, {"id": "fat-olive-oil", "servings": 1}], "total_calories": 352, "total_protein_g": 28, "total_carbs_g": 7, "total_fat_g": 25}, {"meal": "Lunch", "items": [{"id": "protein-salmon", "servings": 1.5}, {"id": "veg-avocado", "servings": 1}, {"id": "veg-broccoli", "servings": 1}], "total_calories": 489, "total_protein_g": 36, "total_carbs_g": 16, "total_fat_g": 32}, {"meal": "Dinner", "items": [{"id": "protein-beef", "servings": 1.5}, {"id": "veg-spinach", "servings": 2}, {"id": "fat-olive-oil", "servings": 2}], "total_calories": 614, "total_protein_g": 42, "total_carbs_g": 7, "total_fat_g": 48}], "daily_totals": {"calories": 1455, "protein_g": 106, "carbs_g": 30, "fat_g": 105}},
    ],
    "mediterranean": [
        {"day": 1, "meals": [{"meal": "Breakfast", "items": [{"id": "dairy-greek-yogurt", "servings": 1}, {"id": "fruit-blueberries", "servings": 1}, {"id": "fat-almonds", "servings": 0.5}], "total_calories": 367, "total_protein_g": 26, "total_carbs_g": 22, "total_fat_g": 13}, {"meal": "Lunch", "items": [{"id": "protein-chickpeas", "servings": 1.5}, {"id": "grain-quinoa", "servings": 1}, {"id": "veg-spinach", "servings": 2}, {"id": "fat-olive-oil", "servings": 1}], "total_calories": 473, "total_protein_g": 21, "total_carbs_g": 46, "total_fat_g": 23}, {"meal": "Dinner", "items": [{"id": "protein-salmon", "servings": 1}, {"id": "veg-sweet-potato", "servings": 1}, {"id": "veg-broccoli", "servings": 1.5}, {"id": "fat-olive-oil", "servings": 1}], "total_calories": 466, "total_protein_g": 29, "total_carbs_g": 32, "total_fat_g": 24}], "daily_totals": {"calories": 1306, "protein_g": 76, "carbs_g": 100, "fat_g": 60}},
    ],
    "diabetes_management": [
        {"day": 1, "meals": [{"meal": "Breakfast", "items": [{"id": "dairy-greek-yogurt", "servings": 1}, {"id": "fruit-blueberries", "servings": 0.75}, {"id": "fat-almonds", "servings": 0.5}], "total_calories": 330, "total_protein_g": 24, "total_carbs_g": 18, "total_fat_g": 12}, {"meal": "Lunch", "items": [{"id": "protein-chicken-breast", "servings": 1.5}, {"id": "grain-quinoa", "servings": 0.75}, {"id": "veg-broccoli", "servings": 2}, {"id": "fat-olive-oil", "servings": 0.5}], "total_calories": 437, "total_protein_g": 52, "total_carbs_g": 25, "total_fat_g": 13}, {"meal": "Dinner", "items": [{"id": "protein-salmon", "servings": 1}, {"id": "veg-spinach", "servings": 2}, {"id": "veg-sweet-potato", "servings": 0.75}, {"id": "fat-olive-oil", "servings": 1}], "total_calories": 410, "total_protein_g": 28, "total_carbs_g": 22, "total_fat_g": 23}], "daily_totals": {"calories": 1177, "protein_g": 104, "carbs_g": 65, "fat_g": 48}},
    ],
}

DIETARY_PATTERN_KEYWORDS: dict[str, str] = {
    "vegan": "vegan_high_protein",
    "vegetarian": "vegan_high_protein",
    "keto": "keto_standard",
    "low-carb": "keto_standard",
    "mediterranean": "mediterranean",
    "heart health": "mediterranean",
    "blood-sugar": "diabetes_management",
    "diabetes": "diabetes_management",
    "weight loss": "weight_loss_omnivore",
}

DEFAULT_MEAL_PLAN = "weight_loss_omnivore"
DANGEROUS_CALORIE_THRESHOLD = 1200
CLINICAL_THERAPY_KEYWORDS = [
    "treat your", "lower your A1C", "cure your", "prescribe",
    "instead of your medication", "you don't need your medication",
    "this will treat", "therapeutic dose",
]
SAFETY_NETTING_DISCLAIMER = (
    "Please remember that this meal plan is for general informational and "
    "educational purposes only. It is not a substitute for professional "
    "medical advice, diagnosis, or treatment. Always consult a qualified "
    "healthcare provider or registered dietitian before making significant "
    "changes to your diet, especially if you have a medical condition or "
    "are taking medication."
)
