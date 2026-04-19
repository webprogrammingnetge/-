import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QScrollArea, QFrame, QLabel, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QThread
from PyQt6.QtGui import QIcon, QFont, QColor
import theme
from theme import THEME
from gui_components import ArticleCard, SearchField, ArticleDetailsWindow
from database_manager import DatabaseManager
from ai_engine import AIEngine
import data_loader

# აბრევიატურების ლექსიკონი სწრაფი ამოცნობისთვის
ABBREVIATIONS = {
    "სსკ": "საქართველოს სისხლის სამართლის კოდექსი",
    "სსსკ": "საქართველოს სისხლის სამართლის საპროცესო კოდექსი",
    "სამოქალაქო": "საქართველოს სამოქალაქო კოდექსი",
    "სასსკ": "საქართველოს სამოქალაქო საპროცესო კოდექსი",
    "ზაკ": "საქართველოს ზოგადი ადმინისტრაციული კოდექსი",
    "ასკ": "საქართველოს ადმინისტრაციული საპროცესო კოდექსი",
    "ასსკ": "საქართველოს ადმინისტრაციულ სამართალდარღვევათა კოდექსი",
    "კონსტიტუცია": "საქართველოს კონსტიტუცია"
}

class PreloadWorker(QThread):
    """ფონური მუშაკი მოდელის გადასახურებლად."""
    finished = pyqtSignal()

    def __init__(self, db):
        super().__init__()
        self.db = db

    def run(self):
        self.db.semantic_engine.preload()
        self.finished.emit()

class SearchWorker(QThread):
    """ეს კლასი უზრუნველყოფს, რომ პროგრამა დარჩეს სწრაფი და მოქნილი (არ გაიჭედოს) მაშინაც კი, როდესაც AI მოდელი ათასობით მუხლს შორის ეძებს ინფორმაციას."""
    results_ready = pyqtSignal(list, str) # შედეგები და კითხვა

    def __init__(self, db, query, law_filter):
        super().__init__()
        self.db = db
        self.query = query
        self.law_filter = law_filter

    def run(self):
        results = self.db.search_articles_semantic(self.query, self.law_filter)
        self.results_ready.emit(results, self.query)

class AIStreamWorker(QThread):
    """ცალკე ნაკადი AI სტრიმინგისთვის — ტექსტს ნაწილ-ნაწილ აწვდის UI-ს."""
    chunk_received = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, ai_engine, articles, user_query=None):
        super().__init__()
        self.ai_engine = ai_engine
        self.articles = articles
        self.user_query = user_query
        self._is_cancelled = False

    def run(self):
        """ფონურ ნაკადში AI სტრიმინგის გაშვება."""
        try:
            for chunk in self.ai_engine.analyze_articles_stream(self.articles, self.user_query):
                if self._is_cancelled:
                    break
                self.chunk_received.emit(chunk)
        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()

    def cancel(self):
        """ანალიზის გაუქმება."""
        self._is_cancelled = True

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("იურიდიული ასისტენტი")
        self.setMinimumSize(1000, 700)
        
        # ბაზასთან და AI-სთან კავშირი
        self.db = DatabaseManager()
        self.ai_engine = AIEngine()
        self.selected_articles = []
        self.pending_ai_explanation = False
        self.ai_stream_worker = None
        self.last_query = None
        
        # მთავარი ვიჯეტი და Layout
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # ზედა ნავიგაცია (Header)
        header = QFrame()
        header.setFixedHeight(60)
        header.setObjectName("Header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        logo = QLabel("იურიდიული ასისტენტი - კანონები და დოკუმენტები")
        logo.setObjectName("Logo")
        header_layout.addWidget(logo)
        header_layout.addStretch()
        
        # შუა ნაწილი (მუხლების სია)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("MainScroll")
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.scroll_content = QWidget()
        self.articles_layout = QVBoxLayout(self.scroll_content)
        self.articles_layout.setContentsMargins(40, 20, 40, 20)
        self.articles_layout.setSpacing(15)
        self.articles_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.scroll_content)
        
        # ქვედა ნაწილი (Gemini-ს სტილის საძიებო ველი)
        footer_container = QWidget()
        footer_layout = QVBoxLayout(footer_container)
        footer_layout.setContentsMargins(40, 20, 40, 30) # დაემატა 20px ზემოდან დაშორება
        
        self.search_section = SearchField()
        self.search_section.law_selected.connect(self.on_law_selected)
        self.search_section.search_triggered.connect(self.search_articles)
        
        # AI ანალიზის მცურავი ღილაკი
        self.ai_btn_container = QWidget()
        ai_btn_layout = QHBoxLayout(self.ai_btn_container)
        ai_btn_layout.setContentsMargins(0, 0, 0, 10)
        self.ai_btn = QPushButton("✨ AI ანალიზი (0)")
        self.ai_btn.setObjectName("AIButton")
        self.ai_btn.setFixedSize(200, 45)
        self.ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ai_btn.setVisible(False)
        self.ai_btn.clicked.connect(self.run_ai_analysis)
        ai_btn_layout.addWidget(self.ai_btn)
        
        footer_layout.addWidget(self.ai_btn_container)
        footer_layout.addWidget(self.search_section)
        
        # კომპონენტების დამატება მთავარ Layout-ში
        self.main_layout.addWidget(header)
        
        # შედეგების არესთვის "კონტეინერი" ჩარჩოთი
        results_frame = QFrame()
        results_frame.setObjectName("ResultsContainer")
        self.results_frame_layout = QVBoxLayout(results_frame)
        self.results_frame_layout.setContentsMargins(1, 1, 1, 1)
        
        # ფიქსირებული შეჯამების ზონა (სქროლის ზემოთ)
        self.summary_container = QWidget()
        self.summary_layout = QVBoxLayout(self.summary_container)
        self.summary_layout.setContentsMargins(0, 0, 0, 0)
        self.summary_layout.setSpacing(0)
        
        self.results_frame_layout.addWidget(self.summary_container)
        self.results_frame_layout.addWidget(self.scroll_area)
        
        # გარე დაშორება ჩარჩოსთვის
        wrapper_layout = QVBoxLayout()
        wrapper_layout.setContentsMargins(40, 10, 40, 10)
        wrapper_layout.addWidget(results_frame)
        
        self.main_layout.addLayout(wrapper_layout)
        self.main_layout.addWidget(footer_container)
        
        self.setStyleSheet(theme.get_stylesheet())
        
        # მოდელის წინასწარი ჩატვირთვა ფონში
        self.preload_worker = PreloadWorker(self.db)
        self.preload_worker.start()
        
        # ძებნის მუშაკი (Search Worker) - ინიციალიზაცია
        self.search_worker = None
        
        # მონაცემების ჩატვირთვა
        self.load_real_data()

    def load_real_data(self):
        """ტვირთავს რეალურ მონაცემებს ბაზიდან."""
        all_laws = self.db.get_all_law_names()
        
        # საძიებო მენიუს შევსება
        self.search_section.set_laws_menu(all_laws)

    def add_article_card(self, law_title, article_no, content):
        card = ArticleCard(law_title, article_no, content)
        # მონიშვნის სიგნალის დაკავშირება
        card.clicked.connect(lambda selected: self.on_article_toggled(selected, card.article_data))
        card.double_clicked.connect(self.open_article_details)
        self.articles_layout.addWidget(card)

    def on_article_toggled(self, is_selected, article_data):
        """მართავს მონიშნულ მუხლებს."""
        if is_selected:
            if article_data not in self.selected_articles:
                self.selected_articles.append(article_data)
        else:
            if article_data in self.selected_articles:
                self.selected_articles.remove(article_data)
        
        # ღილაკის განახლება
        count = len(self.selected_articles)
        self.ai_btn.setText(f"✨ AI ანალიზი ({count})")
        self.ai_btn.setVisible(count > 0)

    def on_law_selected(self, law_name):
        self.search_section.add_tag(law_name)

    def _extract_topic(self, query, triggers):
        """გამოყოფს საძიებო თემას AI ბრძანებიდან."""
        topic = query.lower()
        for trig in triggers:
            topic = topic.replace(trig, "")
        
        # დამატებითი სიტყვების მოცილება
        cleanups = ["ადამიანურ ენაზე", "მარტივად", "გამიგებად", "დამიღეჭე", "დაწვრილებით"]
        for word in cleanups:
            topic = topic.replace(word, "")
            
        return topic.strip()

    def _transliterate_to_georgian(self, text):
        """
        ლათინური სიმბოლოების ქართულ სიმბოლოებად გარდაქმნა.
        ქართული ონლაინ ტრანსლიტერაციის სტანდარტი (მიმართულება: QWERTY → ქართული).
        მხოლოდ ლათინური სიმბოლოები გარდაიქმნება — ქართულები უცვლელად რჩება.
        """
        # uppercase სპეციალური სიმბოლოები (ჯერ uppercase შემოწმება, შემდეგ lowercase)
        mapping = [
            ("sh", "შ"), ("ch", "ჩ"), ("ts", "ც"), ("dz", "ძ"), ("zh", "ჟ"),
            ("gh", "ღ"), ("kh", "ხ"), ("th", "თ"),
            ("T",  "თ"), ("S",  "შ"), ("C",  "ჩ"), ("Z",  "ძ"), ("W",  "ჭ"),
            ("R",  "ღ"), ("J",  "ჟ"),
            ("a", "ა"), ("b", "ბ"), ("g", "გ"), ("d", "დ"), ("e", "ე"),
            ("v", "ვ"), ("z", "ზ"), ("i", "ი"), ("k", "კ"), ("l", "ლ"),
            ("m", "მ"), ("n", "ნ"), ("o", "ო"), ("p", "პ"), ("r", "რ"),
            ("s", "ს"), ("t", "ტ"), ("u", "უ"), ("f", "ფ"), ("q", "ყ"),
            ("x", "ხ"), ("j", "ჯ"), ("h", "ჰ"), ("w", "წ"), ("c", "ც"),
            ("y", "ყ"),
        ]

        result = []
        i = 0
        while i < len(text):
            ch = text[i]
            # ქართული სიმბოლო — უცვლელად გადაიტანება
            if '\u10d0' <= ch <= '\u10ff':
                result.append(ch)
                i += 1
                continue
            # სფართვო (space, პუნქტუაცია) — უცვლელად
            if not ch.isalpha():
                result.append(ch)
                i += 1
                continue
            # ლათინური — ვეძებთ mapping-ში
            matched = False
            for lat, geo in mapping:
                if text[i:i+len(lat)] == lat:
                    result.append(geo)
                    i += len(lat)
                    matched = True
                    break
            if not matched:
                result.append(ch)
                i += 1

        return "".join(result)

    def _find_law_by_fuzzy(self, query):
        """
        text საქაღალდის ფაილებში fuzzy ძებნა (დინამიური).
        აბრუნებს ყველა შესაბამის დამთხვევას — [(law_name, path), ...].
        საქაღალდე ყოველ გამოძახებაზე ახლიდან იკითხება.
        """
        import os
        text_dir = os.path.join(os.path.dirname(__file__), "text")
        if not os.path.exists(text_dir):
            return []

        # text საქაღალდე დინამიურად — ყოველ ჯერზე ახლიდან
        law_files = [f[:-4] for f in os.listdir(text_dir) if f.endswith(".txt")]

        # 1. ABBREVIATIONS-ში ზუსტი დამთხვევა → ერთი შედეგი პირდაპირ
        abbr_match = ABBREVIATIONS.get(query.strip())
        if abbr_match:
            for law in law_files:
                if abbr_match.lower() in law.lower():
                    return [(law, os.path.join(text_dir, law + ".txt"))]

        # 2. Fuzzy ძებნა: კითხვის სიტყვები ფაილის სახელში
        query_words = [w for w in query.lower().split() if len(w) >= 3]
        if not query_words:
            return []

        # ყველა კანდიდატი ქულებით
        scored = []
        for law in law_files:
            law_lower = law.lower()
            score = sum(1 for w in query_words if w in law_lower)
            if score > 0:
                scored.append((score, law))

        if not scored:
            return []

        # მაქსიმალური ქულა
        max_score = max(s for s, _ in scored)
        # ყველა ვინც მაქსიმალურ ქულაზეა → არჩევანი
        matches = [
            (law, os.path.join(text_dir, law + ".txt"))
            for score, law in scored
            if score == max_score
        ]
        return matches

    def _show_law_selector(self, matches):
        """
        HTML-სტილის custom დიალოგი კანონის ასარჩევად.
        matches = [(law_name, path), ...]
        აბრუნებს არჩეულ (law_name, path) ან (None, None).
        """
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QScrollArea, QWidget
        from PyQt6.QtCore import Qt

        dialog = QDialog(self)
        dialog.setWindowTitle("კანონის არჩევა")
        dialog.setObjectName("LawSelectorDialog")
        dialog.setMinimumWidth(520)
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # სათაური
        title = QLabel("🔎 მოიძებნა რამდენიმე კანონი. გთხოვთ აირჩიოთ:")
        title.setObjectName("SelectorTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        # არჩეული კანონი (კლოჟერი)
        selected = [None]

        # ღილაკები თითოეული კანონისთვის
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        btn_widget = QWidget()
        btn_layout = QVBoxLayout(btn_widget)
        btn_layout.setSpacing(8)

        for law_name, law_path in matches:
            btn = QPushButton(law_name)
            btn.setObjectName("LawSelectorBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(44)
            # ღილაკზე დაჭერისას — არჩევა და დახურვა
            def make_handler(n, p):
                def handler():
                    selected[0] = (n, p)
                    dialog.accept()
                return handler
            btn.clicked.connect(make_handler(law_name, law_path))
            btn_layout.addWidget(btn)

        scroll.setWidget(btn_widget)
        layout.addWidget(scroll)

        # გაუქმების ღილაკი
        cancel_btn = QPushButton("გაუქმება")
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(dialog.reject)
        layout.addWidget(cancel_btn)

        # დიალოგის სტილი — theme.py-ს ფერებით
        dialog.setStyleSheet(f"""
            QDialog#LawSelectorDialog {{
                background-color: {THEME['color_bg']};
            }}
            QLabel#SelectorTitle {{
                color: {THEME['color_primary']};
                font-family: "{THEME['font_family_main']}";
                font-size: 11pt;
                font-weight: bold;
                padding-bottom: 8px;
            }}
            QPushButton#LawSelectorBtn {{
                background-color: {THEME['color_white']};
                color: {THEME['color_text']};
                border: 1px solid {THEME['color_search_border']};
                border-radius: 8px;
                font-family: "{THEME['font_family_main']}";
                font-size: 11pt;
                padding: 10px 16px;
                text-align: left;
            }}
            QPushButton#LawSelectorBtn:hover {{
                border-color: {THEME['color_secondary']};
                background-color: {THEME['color_selected_bg']};
                color: {THEME['color_primary']};
            }}
            QPushButton#CancelBtn {{
                background-color: transparent;
                color: {THEME['color_secondary']};
                border: 1px solid {THEME['color_search_border']};
                border-radius: 8px;
                font-family: "{THEME['font_family_ui']}";
                font-size: 10pt;
                padding: 8px;
            }}
            QPushButton#CancelBtn:hover {{
                color: {THEME['color_primary']};
                border-color: {THEME['color_secondary']};
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)


        dialog.exec()
        if selected[0]:
            return selected[0]
        return None, None


    def search_articles(self, query):
        """მთავარი ძებნის და ბრძანებების დამუშავება."""
        if not query.strip():
            return

        # ლათინური → ქართული ავტომატური გარდაქმნა (transliteration)
        query = self._transliterate_to_georgian(query)

        # 1. ბრძანების შემოწმება (Command Parsing)
        lower_query = query.lower().strip()

        
        # AI მოთხოვნის შემოწმება ("ამიხსენი" და სხვა)
        ai_triggers = ["ამიხსენი", "გამიმარტე", "გასაგებად", "რა წერია", "დამიღეჭე"]
        if any(trig in lower_query for trig in ai_triggers):
            if not self.selected_articles:
                # თუ არაფერია მონიშნული, ჯერ ვეძებთ თემას
                topic = self._extract_topic(lower_query, ai_triggers)
                if topic:
                    self.pending_ai_explanation = True
                    # ვუშვებთ სუფთა ძებნას
                    self.search_articles(topic)
                    return
                else:
                    self.add_summary_card("გთხოვთ მიუთითოთ თემა, რისი ახსნაც გსურთ.")
                    return
            self.run_ai_analysis(lower_query)
            return
            
        # "მაჩვენე" ბრძანების ვარიანტები (მართლწერის შეცდომების გათვალისწინება)
        machvene_variants = ["მაჩვენე", "მაცვენე", "მაჩვbene", "macvene", "machvene"]
        machvene_match = next((v for v in machvene_variants if lower_query.startswith(v)), None)
        if machvene_match:
            target = lower_query.replace(machvene_match, "").strip()

            # Fuzzy ძებნა text საქაღალდეში (დინამიური)
            matches = self._find_law_by_fuzzy(target)

            if not matches:
                # ვერ მოიძებნა
                self.clear_results()
                self.search_section.clear_input()
                self.add_summary_card(f"⚠️ კანონი ვერ მოიძებნა: '{target}'")
                return

            # ერთი დამთხვევა → პირდაპირ ვხსნით
            if len(matches) == 1:
                law_name, law_path = matches[0]
            else:
                # მრავალი დამთხვევა → მომხმარებელი ირჩევს
                result = self._show_law_selector(matches)
                if result is None or result == (None, None):
                    return  # გაუქმდა
                law_name, law_path = result

            # ბაზიდან ვცდი ამოღებას პირველ რიგში
            full_text = self.db.get_full_law_text(law_name)
            # თუ ბაზაში არ არის, პირდაპირ ფაილიდან ვკითხულობ
            if not full_text:
                try:
                    with open(law_path, "r", encoding="utf-8") as f:
                        full_text = f.read()
                except Exception:
                    full_text = None

            if full_text:
                self.clear_results()
                self.search_section.clear_input()
                self.open_article_details({
                    "title": law_name,
                    "article_no": "სრული ტექსტი",
                    "content": full_text
                })
            else:
                self.add_summary_card(f"⚠️ ფაილის წაკითხვა ვერ მოხერხდა: '{law_name}'")
            return


        # 2. სემანტიკური ძებნა ფონურ ნაკადში (Threading)
        self.clear_results()
        self.search_section.clear_input()
        self.add_summary_card(f"მიმდინარეობს ძებნა: \"{query}\"...")
        
        law_filter = self.search_section.get_active_tags()
        
        # თუ ძველი ძებნა ჯერ კიდევ მუშაობს, გავაჩეროთ
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.terminate()
            self.search_worker.wait()
            
        self.search_worker = SearchWorker(self.db, query, law_filter)
        self.search_worker.results_ready.connect(self.display_search_results)
        self.search_worker.start()

    def display_search_results(self, results, query):
        """ძებნის შედეგების ჩვენება UI-ზე."""
        self.clear_results()
        
        count = len(results)
        self.last_query = query
        
        if getattr(self, 'pending_ai_explanation', False):
            summary_text = f"✨ მოიძებნა შესაბამისი მუხლები თემაზე: \"{query}\". \nგთხოვთ **მონიშნოთ** სასურველი მუხლები და დააჭიროთ **'AI ანალიზს'**."
            self.pending_ai_explanation = False # დროშის ჩამოყრა
        else:
            summary_text = f"თქვენ ეძებდით: \"{query}\". მოიძებნა {count} მუხლი."
            
        self.add_summary_card(summary_text)

        if not results:
            self.add_error_message("საძიებო სიტყვით მუხლები ვერ მოიძებნა. სცადეთ სხვა სიტყვა.")
        else:
            for art in results:
                # დამთხვევის პროცენტის ფორმატირება (თუ არსებობს)
                similarity = art.get("cosine_similarity")
                if similarity is not None:
                    pct = int(similarity * 100)
                    title_with_pct = f"{art['law_name']} (დამთხვ. {pct}%)"
                else:
                    title_with_pct = art["law_name"]
                self.add_article_card(title_with_pct, f"მუხლი {art['article_no']}", art["content"])

    def add_error_message(self, text):
        """წითელი ფერის შეტყობინების დამატება."""
        error_label = QLabel(text)
        error_label.setObjectName("ErrorLabel")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.articles_layout.addWidget(error_label)

    def add_summary_card(self, text):
        """ამატებს შეჯამების ბარათს ფიქსირებულ ზონაში."""
        card = QFrame()
        card.setObjectName("SummaryCard")
        layout = QVBoxLayout(card)
        
        label = QLabel(text)
        label.setObjectName("SummaryLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        layout.addWidget(label)
        self.summary_layout.addWidget(card)

    def clear_results(self):
        """ასუფთავებს ძებნის შედეგებს."""
        # მუხლების გასუფთავება
        while self.articles_layout.count():
            item = self.articles_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # შეჯამების გასუფთავება
        while self.summary_layout.count():
            item = self.summary_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def open_article_details(self, data):
        """ხსნის მუხლის დეტალურ ფანჯარას ორმაგი კლიკისას."""
        self.details_window = ArticleDetailsWindow(data["title"], data["article_no"], data["content"], search_query=self.last_query)
        self.details_window.show()

    def run_ai_analysis(self, custom_query=None):
        """უშვებს AI ანალიზს სტრიმინგ რეჟიმში ცალკე ნაკადში."""
        if not self.selected_articles:
            return

        # თუ უკვე მიმდინარეობს ანალიზი — გაუქმება
        if self.ai_stream_worker and self.ai_stream_worker.isRunning():
            self.ai_stream_worker.cancel()
            self.ai_stream_worker.wait(2000)
            self._on_ai_finished()
            return

        # ინტერფეისის დაბლოკვა
        self.search_section.search_btn.setEnabled(False)
        self.ai_btn.setText("⏳ გაუქმება")

        self.add_summary_card("✨ Gemini აანალიზებს მუხლებს...")

        # სტრიმინგ ფანჯრის გახსნა ცარიელი ტექსტით
        self.ai_window = ArticleDetailsWindow("✨ AI ანალიზი (Gemini)", "კონტექსტური განმარტება", "")
        self.ai_window.show()

        # ცალკე ნაკადის გაშვება
        self.ai_stream_worker = AIStreamWorker(self.ai_engine, self.selected_articles, custom_query)
        self.ai_stream_worker.chunk_received.connect(self.ai_window.append_text)
        self.ai_stream_worker.finished_signal.connect(self._on_ai_finished)
        self.ai_stream_worker.error_signal.connect(lambda err: self.ai_window.append_text(f"\n\nშეცდომა: {err}"))
        self.ai_stream_worker.start()

    def _on_ai_finished(self):
        """AI ანალიზის დასრულების შემდეგ ინტერფეისის განბლოკვა."""
        self.search_section.search_btn.setEnabled(True)
        count = len(self.selected_articles)
        self.ai_btn.setText(f"✨ AI ანალიზი ({count})")

    def closeEvent(self, event):
        """პროგრამის დახურვისას ყველა ფონური ნაკადის გაჩერება."""
        # AI სტრიმინგის ნაკადის გაჩერება
        if self.ai_stream_worker and self.ai_stream_worker.isRunning():
            self.ai_stream_worker.cancel()
            self.ai_stream_worker.wait(2000)
        # ძებნის ნაკადის გაჩერება
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.terminate()
            self.search_worker.wait(2000)
        # მოდელის წინასწარი ჩატვირთვის ნაკადის გაჩერება
        if self.preload_worker and self.preload_worker.isRunning():
            self.preload_worker.terminate()
            self.preload_worker.wait(2000)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # "Nuclear" ფიქსი: აიძულებს Qt-ს გამოიყენოს ვალიდური ზომა პირველივე სტილის პარსინგისას
    # app.setStyleSheet(" * { font-size: 11pt; } ")
    
    # გლობალური ფონტის დაყენება
    main_font = QFont(theme.THEME['font_family_ui'])
    main_font.setPointSize(max(8, theme.THEME['font_size_ui']))
    app.setFont(main_font)
    
    # გლობალური სტილის დაყენება
    app.setStyleSheet(theme.get_stylesheet())
    
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())