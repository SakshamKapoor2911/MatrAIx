# Ecommerce product discovery

You're shopping on a small ecommerce site at:

http://ecommerce-web:8000/

Browse in the browser. Decide what kind of product you realistically need today and what constraints matter — price, quality, space, style, durability, ease of setup, and so on. Explore the catalog and product details, compare at least two products, and pick one item you would seriously consider.

Do not place an order or enter payment details. We're evaluating the shopping and product-discovery experience.

When you're done, submit your result as JSON in your final answer. Do not use Save dialogs or manual file editing.

```json
{
  "selected_product_id": "<product id shown on the site>",
  "selected_product_name": "<product name shown on the site>",
  "need_satisfaction": 1,
  "ease_of_use": 1,
  "overall_experience_rating": 1,
  "reason": "<why this product and experience fit or did not fit your needs>"
}
```

Ratings must be integers from 1 to 10. Use only product ids and names shown on the site.
