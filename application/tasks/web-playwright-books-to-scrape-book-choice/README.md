# web-books-to-scrape_book-choice

Web browsing task where an agent navigates Books to Scrape (`https://books.toscrape.com/`) to choose a book based on genre and budget preferences.

## Persona Stratification
- `genre_preference`: `fiction`, `non_fiction`, `science_fiction`, `mystery`, `history`
- `budget_range`: `budget`, `moderate`, `premium`

## Oracle Solution
```bash
bash solution/solve.sh
```

## Verifier Test
```bash
bash tests/test.sh
```
