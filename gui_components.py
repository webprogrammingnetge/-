from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QTextEdit, QPushButton, QGraphicsDropShadowEffect, QMainWindow, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont
from theme import THEME
import markdown

class CustomTextEdit(QTextEdit):
    """
    QTextEdit Ctrl+Enter მხარდაჭერით.
    """
    search_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont(THEME['font_family_ui'], 11))

    def keyPressEvent(self, event):
        is_enter = event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        has_ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        
        if is_enter and not has_ctrl:
            self.search_requested.emit()
            return
        
        if is_enter and has_ctrl:
            self.insertPlainText("\n")
            return
            
        super().keyPressEvent(event)

class TagWidget(QFrame):
    """
    არჩეული კანონის ვიზუალური ტეგი (ბუშტი).
    """
    closed = pyqtSignal(object)

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setObjectName("TagWidget")
        self.setFixedHeight(24)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(5)
        
        label = QLabel(text)
        label.setObjectName("TagLabel")
        
        # გრძელი ტექსტის შემოკლება
        full_text = text
        metrics = label.fontMetrics()
        elided_text = metrics.elidedText(text, Qt.TextElideMode.ElideRight, 180)
        label.setText(elided_text)
        self.setToolTip(full_text)
        
        close_btn = QPushButton("×")
        close_btn.setObjectName("TagCloseBtn")
        close_btn.setFixedSize(16, 16)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(lambda: self.closed.emit(self))
        
        layout.addWidget(label)
        layout.addWidget(close_btn)

class ArticleDetailsWindow(QMainWindow):
    """
    ცალკე ფანჯარა მუხლის სრული ტექსტის საჩვენებლად.
    საძიებო სიტყვის შემცველი წინადადებები ყვითლად გამოიყოფა.
    """
    def __init__(self, title, article_no, content, parent=None, search_query=None):
        super().__init__(parent)
        self.setWindowTitle(f"{title} - {article_no}")
        self.setObjectName("DetailsWindow")
        
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        width = int(screen.width() * 0.8)
        height = int(screen.height() * 0.8)
        self.resize(width, height)
        
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.move(x, y)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        title_label = QLabel(title)
        title_label.setObjectName("DetailsTitle")
        title_label.setWordWrap(True)
        
        display_no = article_no
        if "მუხლი" in article_no:
            display_no = article_no.replace("მუხლი", "").strip()
            
        no_label = QLabel(f"მუხლი: {display_no}")
        no_label.setObjectName("DetailsNo")
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("DetailsLine")
        
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        self.content_text.setObjectName("DetailsContent")
        
        content_font = QFont(THEME['font_family_main'])
        content_font.setPointSize(max(8, THEME['font_size_main']))
        self.content_text.setFont(content_font)
        
        # Markdown → HTML გარდაქმნა და ჩვენება
        html_body = markdown.markdown(
            content or "",
            extensions=["tables", "nl2br"]
        )
        # ჰაილაითის ლოგიკა (search_query-ს გამოყენებით)
        if search_query:
            highlighted_html = self._highlight_sentences(html_body, search_query)
            html_body = highlighted_html

        # CSS — theme.py-ს ფერებით
        styled_html = f"""
        <html><head><style>
            body {{
                font-family: '{THEME['font_family_main']}', serif;
                font-size: {THEME['font_size_main']}pt;
                color: {THEME['color_text']};
                line-height: 1.7;
                margin: 12px;
            }}
            h1, h2, h3 {{
                color: {THEME['color_primary']};
                font-family: '{THEME['font_family_main']}', serif;
                border-bottom: 1px solid {THEME['color_search_border']};
                padding-bottom: 4px;
                margin-top: 18px;
            }}
            h1 {{ font-size: 15pt; }}
            h2 {{ font-size: 13pt; }}
            h3 {{ font-size: 12pt; }}
            strong {{ color: {THEME['color_primary']}; }}
            em {{ color: {THEME['color_secondary']}; }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 8px 0;
            }}
            th, td {{
                border: 1px solid {THEME['color_search_border']};
                padding: 6px 10px;
                text-align: left;
            }}
            th {{ background-color: {THEME['color_bg']}; }}
        </style></head><body>{html_body}</body></html>
        """
        self.content_text.setHtml(styled_html)
        
        layout.addWidget(title_label)
        layout.addWidget(no_label)
        layout.addWidget(line)
        layout.addWidget(self.content_text)

    def _highlight_sentences(self, content, search_query):
        """
        საძიებო სიტყვის შემცველ წინადადებებს ყვითელი ფონით მონიშნავს.
        წინადადება = წერტილიდან წერტილამდე ტექსტი.
        """
        import re
        # საძიებო სიტყვების ფუძეების ამოღება (მინ. 4 სიმბოლო)
        query_words = search_query.lower().split()
        stems = [w[:max(4, len(w) - 2)] for w in query_words if len(w) >= 3]

        if not stems:
            return f"<pre style='white-space: pre-wrap;'>{content}</pre>"

        # ტექსტის წინადადებებად დაყოფა (წერტილი, წერტილ-მძიმე, ახალი ხაზი)
        sentences = re.split(r'(?<=[.;।\n])', content)

        html_parts = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            # შემოწმება: შეიცავს თუ არა წინადადება რომელიმე ფუძეს
            is_match = any(stem in sentence_lower for stem in stems)
            if is_match and sentence.strip():
                html_parts.append(
                    f'<span style="background-color: #FFF3CD; padding: 2px 0;">{sentence}</span>'
                )
            else:
                html_parts.append(sentence)

        return f"<pre style='white-space: pre-wrap; font-family: inherit;'>{''.join(html_parts)}</pre>"

    def append_text(self, chunk):
        """სტრიმინგისთვის: ტექსტის ნაწილის თანდათანობით დამატება."""
        cursor = self.content_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.content_text.setTextCursor(cursor)
        self.content_text.ensureCursorVisible()


class ArticleCard(QFrame):
    """
    ბარათი კანონის მუხლის საჩვენებლად.
    """
    clicked = pyqtSignal(bool)
    double_clicked = pyqtSignal(dict)

    def __init__(self, title, article_no, content, parent=None):
        super().__init__(parent)
        self.article_data = {"title": title, "article_no": article_no, "content": content}
        self.is_selected = False
        self.setObjectName("ArticleCard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setObjectName("ArticleTitle")
        
        display_no = article_no
        if "მუხლი" in article_no:
            display_no = article_no.replace("მუხლი", "").strip()
            
        self.no_label = QLabel(f"მუხლი: {display_no}")
        self.no_label.setObjectName("ArticleNo")
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.no_label)
        
        display_content = content
        if len(content) > 280:
            display_content = content[:277] + "..."
            
        self.content_label = QLabel(display_content)
        self.content_label.setWordWrap(True)
        self.content_label.setObjectName("ArticleContent")

        layout.addLayout(header_layout)
        layout.addWidget(self.content_label)
        self.update_style()

    def update_style(self):
        self.setProperty("selected", self.is_selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selected = not self.is_selected
            self.update_style()
            self.clicked.emit(self.is_selected)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.article_data)

class SearchField(QFrame):
    """
    Gemini-ს სტილის საძიებო ველი.
    """
    law_selected = pyqtSignal(str)
    search_triggered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SearchContainer")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)
        
        self.tags_container = QWidget(); self.tags_container.setFixedHeight(35)
        self.tags_container.setVisible(False)
        self.tags_layout = QHBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(8)
        self.tags_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.text_input = CustomTextEdit()
        self.text_input.setPlaceholderText("ჰკითხეთ საძიებო სისტემას...")
        self.text_input.setObjectName("GeminiInput")
        self.text_input.setFrameStyle(QFrame.Shape.NoFrame)
        self.text_input.setMinimumHeight(60)
        self.text_input.setMaximumHeight(150)
        self.text_input.search_requested.connect(self.on_search_clicked)
        
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(5)
        
        plus_btn = QPushButton("+")
        plus_btn.setObjectName("ToolIcon")
        
        self.laws_btn = QPushButton("⚖ კანონები ⌵")
        self.laws_btn.setObjectName("LawsBtn")
        self.laws_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.docs_btn = QPushButton("📄 დოკუმენტები ⌵")
        self.docs_btn.setObjectName("DocsBtn")
        self.docs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        toolbar_layout.addWidget(plus_btn)
        toolbar_layout.addWidget(self.laws_btn)
        toolbar_layout.addWidget(self.docs_btn)
        toolbar_layout.addStretch()
        
        self.search_btn = QPushButton(">")
        self.search_btn.setObjectName("SearchBtn")
        self.search_btn.setFixedSize(38, 38)
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.clicked.connect(self.on_search_clicked)
        
        toolbar_layout.addWidget(self.search_btn)
        
        self.layout.addWidget(self.tags_container)
        self.layout.addWidget(self.text_input, 1)
        toolbar_container = QWidget()
        toolbar_container.setFixedHeight(40)
        toolbar_container.setLayout(toolbar_layout)
        self.layout.addWidget(toolbar_container)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

    def add_tag(self, text):
        self.tags_container.setVisible(True)
        tag = TagWidget(text)
        tag.closed.connect(self.remove_tag)
        self.tags_layout.addWidget(tag)

    def remove_tag(self, tag_widget):
        self.tags_layout.removeWidget(tag_widget)
        tag_widget.deleteLater()
        if self.tags_layout.count() == 0:
            self.tags_container.setVisible(False)

    def clear_input(self):
        self.text_input.clear()

    def get_active_tags(self):
        tags = []
        for i in range(self.tags_layout.count()):
            item = self.tags_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, TagWidget):
                    tags.append(widget.toolTip())
        return tags

    def on_search_clicked(self):
        query = self.text_input.toPlainText().strip()
        if query:
            self.search_triggered.emit(query)

    def set_laws_menu(self, laws):
        menu = self._create_styled_menu()
        for law in laws:
            action = menu.addAction(law)
            action.triggered.connect(lambda checked, l=law: self.law_selected.emit(l))
        self.laws_btn.setMenu(menu)

    def set_docs_menu(self, docs):
        menu = self._create_styled_menu()
        for doc in docs:
            action = menu.addAction(doc)
            action.triggered.connect(lambda checked, d=doc: self.law_selected.emit(d))
        self.docs_btn.setMenu(menu)

    def _create_styled_menu(self):
        menu = QMenu(self)
        return menu
