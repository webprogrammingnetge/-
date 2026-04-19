import sqlite3
import os
from semantic_engine import SemanticEngine

class DatabaseManager:
    def __init__(self, db_path="legal_system.db", index_path="legal_index.faiss"):
        self.db_path = db_path
        self.index_path = index_path
        self.semantic_engine = SemanticEngine(index_path=index_path)
        self._init_db()

    def _init_db(self):
        """ბაზის და ცხრილების ინიციალიზაცია."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # კანონების ცხრილი
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS laws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                law_name TEXT NOT NULL,
                part TEXT,        -- კარი / ნაწილი
                book TEXT,        -- წიგნი
                chapter TEXT,     -- თავი
                article_no TEXT,
                title TEXT,
                content TEXT,
                category TEXT,
                weight REAL DEFAULT 0.8,
                vector_id INTEGER
            )
        ''')
        
        # ინდექსები სწრაფი ძებნისთვის
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_law_name ON laws(law_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_article_no ON laws(article_no)')
        
        conn.commit()
        conn.close()

    def insert_article(self, law_name, article_no, title, content, category="law", part=None, book=None, chapter=None):
        """ახალი მუხლის დამატება იერარქიის გათვალისწინებით."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # წაშლა თუ უკვე არსებობს (სახელი, მუხლი და თავი უნდა ემთხვეოდეს, რადგან ნუმერაცია მეორდება)
        cursor.execute('''
            DELETE FROM laws 
            WHERE law_name = ? AND article_no = ? AND (chapter = ? OR (chapter IS NULL AND ? IS NULL))
        ''', (law_name, article_no, chapter, chapter))
        
        cursor.execute('''
            INSERT INTO laws (law_name, part, book, chapter, article_no, title, content, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (law_name, part, book, chapter, article_no, title, content, category))
        
        conn.commit()
        conn.close()

    def search_articles(self, query, law_filter=None, limit=20):
        """ტექსტური ძებნა (საკვანძო სიტყვების მხარდაჭერით)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # სიტყვების დაყოფა და ფილტრაცია (მოკლე სიტყვების ამოღება)
        keywords = [k.strip() for k in query.split() if len(k.strip()) > 2]
        if not keywords:
            keywords = [query] # თუ მხოლოდ მოკლე სიტყვებია, გამოვიყენოთ მთლიანი query
            
        # SQL-ის აწყობა დინამიურად
        where_clauses = []
        params = []
        for k in keywords:
            where_clauses.append("(content LIKE ? OR title LIKE ?)")
            params.extend([f'%{k}%', f'%{k}%'])
            
        sql = f"SELECT * FROM laws WHERE ({' OR '.join(where_clauses)})"
        
        if law_filter:
            if isinstance(law_filter, list):
                placeholders = ','.join(['?'] * len(law_filter))
                sql += f" AND law_name IN ({placeholders})"
                params.extend(law_filter)
            else:
                sql += " AND law_name = ?"
                params.append(law_filter)
        
        sql += " ORDER BY weight DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        conn.close()
        return [dict(row) for row in rows]

    def search_articles_semantic(self, query, law_filter=None, limit=20):
        """სემანტიკური (ვექტორული) ძებნა რანჟირებით."""
        # 1. FAISS-დან მსგავსი ვექტორების და ქულების ამოღება
        semantic_results = self.semantic_engine.search(query, top_k=limit*2)
        if not semantic_results:
            return self.search_articles(query, law_filter, limit) # Fallback ტექსტურ ძებნაზე

        # vector_id-ების რუკა ქულებთან (Cosine Similarity)
        score_map = {res['vector_id']: res['score'] for res in semantic_results}
        vector_ids = list(score_map.keys())

        # 2. SQLite-დან მონაცემების ამოღება
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        placeholders = ','.join(['?'] * len(vector_ids))
        sql = f"SELECT * FROM laws WHERE vector_id IN ({placeholders})"
        params = vector_ids

        if law_filter:
            if isinstance(law_filter, list):
                f_placeholders = ','.join(['?'] * len(law_filter))
                sql += f" AND law_name IN ({f_placeholders})"
                params.extend(law_filter)
            else:
                sql += " AND law_name = ?"
                params.append(law_filter)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        # 3. რანჟირება: FinalScore = CosineSimilarity * Weight
        processed_results = []
        for row in rows:
            res = dict(row)
            cosine_sim = score_map.get(res['vector_id'], 0)
            
            # კონსტიტუციის პრიორიტეტი (თუ მსგავსება > 0.7)
            weight = res['weight']
            if "კონსტიტუცია" in res['law_name'] and cosine_sim > 0.7:
                weight = 1.2 # გაზრდილი წონა კონსტიტუციისთვის
            
            res['final_score'] = cosine_sim * weight
            res['cosine_similarity'] = cosine_sim
            processed_results.append(res)

        # დალაგება FinalScore-ის მიხედვით
        processed_results.sort(key=lambda x: x['final_score'], reverse=True)
        
        return processed_results[:limit]

    def get_full_law_text(self, law_name):
        """მთლიანი კანონის ტექსტის ამოღება."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM laws 
            WHERE law_name = ? 
            ORDER BY id ASC
        ''', (law_name,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return None
            
        full_text = f"# {law_name}\n\n"
        for row in rows:
            full_text += f"## მუხლი {row['article_no']}. {row['title']}\n"
            full_text += f"{row['content']}\n\n"
            
        return full_text

    def get_all_law_names(self):
        """ყველა არსებული კანონის სახელის ამოღება."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT law_name FROM laws")
        names = [row[0] for row in cursor.fetchall()]
        conn.close()
        return names

    def clear_database(self):
        """ბაზის სრულად გასუფთავება."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM laws")
        conn.commit()
        conn.close()

