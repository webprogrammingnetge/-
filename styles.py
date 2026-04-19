from theme import THEME

def get_base_qss():
    """აბრუნებს ძირითად QSS სტილებს theme.py-ზე დაყრდნობით"""
    return f"""
    QMainWindow {{
        background-color: {THEME['color_bg']};
    }}
    
    /* ScrollArea სტილი */
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    
    QScrollBar:vertical {{
        border: none;
        background: {THEME['color_bg']};
        width: 10px;
        margin: 0px 0px 0px 0px;
    }}
    
    QScrollBar::handle:vertical {{
        background: {THEME['color_accent']};
        min-height: 20px;
        border-radius: 5px;
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        border: none;
        background: none;
    }}
    """
