# Ecommerce product discovery

You are using a small ecommerce platform at:

http://ecommerce-web:8000/

Browse the site in the browser. Based on your persona, silently decide what kind
of product you realistically need today and what constraints matter to you, such
as price, quality, space, style, durability, or ease of setup. Explore the
catalog and product details, compare at least two products, and choose one item
you would seriously consider.

Do not place an order or enter payment details. The task is to evaluate the
shopping and product-discovery experience.

When you are done, submit your result as JSON with a done action. Harbor will
write it to `/app/output/ecommerce_interaction.json`; do not use Save dialogs or
manual file editing.

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

Ratings must be integers from 1 to 10. Use only product ids and names shown on
the site.
