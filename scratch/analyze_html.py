from bs4 import BeautifulSoup
import os

html_path = 'temp_login_error.html'
if not os.path.exists(html_path):
    print("HTML file not found!")
    exit(1)

with open(html_path, 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

with open('scratch/analysis_output.txt', 'w', encoding='utf-8') as out:
    out.write("=== Analyzing page ===\n")
    articles = soup.find_all(attrs={"role": "article"})
    out.write(f"Total role=article: {len(articles)}\n")
    for idx, art in enumerate(articles):
        label = art.get('aria-label', '')
        out.write(f"Article {idx+1}: class={art.get('class', [])} label={repr(label)}\n")
        # Print first child dir=auto text
        dir_autos = art.find_all(lambda tag: tag.name in ['div', 'span'] and tag.get('dir') == 'auto')
        for da in dir_autos:
            out.write(f"  dir=auto: {repr(da.get_text().strip()[:100])}\n")
