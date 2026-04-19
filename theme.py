# დიზაინის სისტემის ცენტრალური ტოქენები
# აქედან ხდება ფერების, ფონტების და ზომების მარტივი ცვლილება

THEME = {
    # ფერების პალიტრა (Academy / Legal Style)
    "color_bg": "#F5F5F5",          # Cream / Paper White
    "color_primary": "#1B263B",     # Deep Legal Blue
    "color_secondary": "#415A77",   # Slate Gray
    "color_accent": "#778DA9",      # Light Steel Blue
    "color_text": "#0D1B2A",        # Near Black (High Contrast)
    "color_white": "#FFFFFF",
    "color_gold": "#D4AF37",        # Metallic Gold for Logo
    
    # მონიშვნის ფერები
    "color_selected_bg": "#E0E7FF", # Light Indigo for selected cards
    "color_selected_border": "#3B82F6", # Blue border for selected cards
    
    # Gemini სტილის საძიებო ველი
    "color_search_bg": "#FFFFFF",
    "color_search_border": "#E5E7EB",
    "search_border_radius": "28px",
    "search_padding": "10px 10px",
    
    # ფონტები
    "font_family_main": "Sylfaen",  # ქართული აკადემიური ფონტი
    "font_family_ui": "Segoe UI",   # სისტემური ინტერფეისისთვის
    "font_size_main": 14,
    "font_size_ui": 12,
    
    # ზომები
    "spacing_xs": "4pt",
    "spacing_sm": "8pt",
    "spacing_md": "16pt",
    "spacing_lg": "24pt",
    "border_radius": "8pt",
    "card_padding": "15pt",
}

# QSS შაბლონისთვის დამხმარე ფუნქცია
def get_stylesheet():
    return f"""
    QMainWindow, #CentralWidget {{
        background-color: {THEME['color_bg']};
    }}
    
    #Header {{
        background-color: {THEME['color_bg']};
        border-bottom: 1px solid {THEME['color_search_border']};
    }}
    
    QWidget {{
        font-family: "{THEME['font_family_ui']}";
        font-size: 10pt;
        color: {THEME['color_text']};
    }}
    
    /* ძირითადი ტექსტის სტილი (აკადემიური) */
    QLabel {{
        font-family: "{THEME['font_family_main']}";
        font-size: 11pt;
    }}
    
    QMenu {{
        font-family: "{THEME['font_family_ui']}";
        font-size: 10pt;
    }}
    
    /* საძიებო ველი */
    QLineEdit {{
        padding: 10px;
        border: 2px solid {THEME['color_secondary']};
        border-radius: {THEME['border_radius']};
        background-color: {THEME['color_white']};
        font-size: 11pt;
    }}
    
    QLineEdit:focus {{
        border: 2px solid {THEME['color_primary']};
    }}
    
    /* ბარათების კონტეინერი */
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    
    /* გვერდითა პანელი */
    #Sidebar {{
        background-color: {THEME['color_primary']};
        border-right: 1px solid {THEME['color_secondary']};
    }}
    
    #Sidebar QLabel {{
        color: {THEME['color_white']};
    }}
    
    #ResultsContainer {{
        background-color: {THEME['color_white']};
        border: 1px solid #d1d5db;
        border-radius: 12px;
    }}
    
    /* AI ანალიზის ღილაკი (განახლების ღილაკის სტილში) */
    #AIButton {{
        background-color: #CCE5FF;
        color: #003366;
        border-radius: 22px;
        font-weight: 500;
        font-size: 11pt;
        border: none;
    }}
    #AIButton:hover {{ 
        background-color: #B2D8FF; 
    }}
    
    /* პატარა ტეგები (კანონის ბუშტები) */
    #TagWidget {{
        background-color: #f8f9fa;
        border: 1px solid #dadce0;
        border-radius: 3px;
    }}
    #TagWidget:hover {{
        background-color: #e4e6eb;
        border-color: {THEME['color_selected_border']};
    }}
    
    #TagCloseBtn {{
        border: none;
        background: transparent;
        color: #999;
        font-weight: bold;
    }}
    #TagCloseBtn:hover {{
        color: #f44336;
    }}
    
    /* მუხლის ბარათები */
    #ArticleCard {{
        background-color: {THEME['color_white']};
        border: 1px solid {THEME['color_search_border']};
        border-radius: 12px;
    }}
    #ArticleCard:hover {{
        border-color: {THEME['color_secondary']};
    }}
    #ArticleCard[selected="true"] {{
        background-color: {THEME['color_selected_bg']};
        border: 2px solid {THEME['color_selected_border']};
    }}
    
    /* საძიებო კონტეინერი (Gemini Style) */
    #SearchContainer {{
        background-color: {THEME['color_search_bg']};
        border: 1.2px solid {THEME['color_search_border']};
        border-radius: {THEME['search_border_radius']};
        padding: 4px 10px;
        margin: 10px 20px;
    }}
    
    #GeminiInput {{
        background: transparent;
        /* border: 1px solid black; წასაშლელია */
        color: {THEME['color_text']};
    }}
    
    #ToolIcon, #LawsBtn {{
        background-color: transparent;
        border: none;
        color: {THEME['color_secondary']};
        border-radius: 8px;
    }}
    #ToolIcon:hover, #LawsBtn:hover {{
        background-color: {THEME['color_bg']};
        color: {THEME['color_primary']};
    }}
    
    /* საძიებო ღილაკი — მინიმალისტური წრიული დიზაინი */
    #SearchBtn {{
        background-color: #D8DEE6;
        color: #1A1A2E;
        border: none;
        border-radius: 19px;
        font-size: 18px;
        font-weight: bold;
    }}
    #SearchBtn:hover {{
        background-color: #C0C8D4;
    }}
    
    /* შეჯამების ბარათი */
    #SummaryCard {{
        background-color: transparent;
        border: none;
    }}

    #SummaryLabel {{
        font-style: italic;
        color: {THEME['color_gold']};
        font-size: 11pt;
    }}

    #Logo {{
        font-weight: bold;
        font-size: 14pt;
        letter-spacing: 1px;
        color: {THEME['color_text']};
    }}

    #ErrorLabel {{
        color: #d32f2f;
        padding: 20px;
        font-size: 11pt;
        font-weight: bold;
    }}
    
    /* კონტექსტური მენიუები */
    QMenu {{
        background-color: {THEME['color_white']};
        border: 1px solid {THEME['color_search_border']};
        border-radius: 8px;
        padding: 5px;
    }}
    QMenu::item {{
        padding: 8px 25px;
        border-radius: 4px;
        color: {THEME['color_text']};
    }}
    QMenu::item:selected {{
        background-color: {THEME['color_bg']};
        color: {THEME['color_primary']};
    }}
    """
