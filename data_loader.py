import json
import os
import re

def load_categorized_laws(settings_path="settings.json"):
    """ტვირთავს კანონებს და დოკუმენტებს ცალ-ცალკე სექციებიდან."""
    result = {"laws": [], "docs": []}
    
    if not os.path.exists(settings_path):
        return result
        
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 1. კანონების ჩატვირთვა (priority_urls)
        priority_urls = data.get("priority_urls", [])
        seen_laws = set()
        for item in priority_urls:
            desc = item.get("description", "").strip()
            if desc and desc not in seen_laws:
                result["laws"].append(desc)
                seen_laws.add(desc)
                
        # 2. დოკუმენტების ჩატვირთვა (document_urls)
        document_urls = data.get("document_urls", [])
        seen_docs = set()
        for item in document_urls:
            desc = item.get("description", "").strip()
            if desc and desc not in seen_docs:
                result["docs"].append(desc)
                seen_docs.add(desc)
                
    except Exception as e:
        print(f"Error loading settings: {e}")
        
    return result

def get_sample_articles(laws_dir="text", limit_per_law=2, total_limit=10):
    """ამოიღებს სატესტო მუხლებს რეალური ფაილებიდან."""
    articles = []
    if not os.path.exists(laws_dir):
        return articles
        
    files = [f for f in os.listdir(laws_dir) if f.endswith(".txt")]
    article_pattern = re.compile(r"^მუხლი\s+(\d+)\.\s+(.*)$")
    
    for filename in files:
        law_name = filename.replace(".txt", "")
        filepath = os.path.join(laws_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content_lines = f.readlines()
                
            count = 0
            for i, line in enumerate(content_lines):
                line = line.strip()
                match = article_pattern.match(line)
                if match:
                    art_no = match.group(1)
                    art_content = ""
                    for next_line in content_lines[i+1 : i+10]:
                        if next_line.startswith("მუხლი"):
                            break
                        if next_line.strip() and not next_line.startswith("---"):
                            art_content += next_line.strip() + " "
                    
                    if art_content:
                        articles.append({
                            "title": law_name,
                            "article_no": art_no,
                            "content": art_content[:300] + "..."
                        })
                        count += 1
                        if count >= limit_per_law:
                            break
                            
            if len(articles) >= total_limit:
                break
        except Exception:
            continue
            
    return articles
