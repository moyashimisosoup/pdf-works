"""Soft Outline tactile buttons, deliberately without animated shadows.

A 3px bottom edge makes the button visibly elevated. While pressed, the
bottom edge becomes 1px, the top edge becomes 3px, and the label moves
down 2px through padding. The outer geometry remains stable in Qt layouts.
"""

BUTTON_STYLE = """
QPushButton {
    color: #351F39;
    background-color: #FCFBF7;
    border: 1px solid #CDC4CF;
    border-bottom: 3px solid #A99DAD;
    border-radius: 12px;
    min-height: 24px;
    padding: 7px 12px;
}
QPushButton:hover {
    background-color: #FFFFFF;
    border-color: #A79AAB;
    border-bottom-color: #877989;
}
QPushButton:pressed {
    background-color: #EFEAF0;
    border: 1px solid #9D92A2;
    border-top: 3px solid #9D92A2;
    border-bottom: 1px solid #9D92A2;
    padding-top: 9px;
    padding-bottom: 5px;
}
QPushButton:focus {
    border-color: #726A95;
    border-bottom-color: #726A95;
}
QPushButton:disabled {
    color: #9B949C;
    background-color: #F6F3F3;
    border: 1px solid #E2DBE0;
    border-bottom: 2px solid #D8D0D4;
}
QPushButton#primary {
    background-color: #E9F1F3;
    border: 1px solid #9BB9C3;
    border-bottom: 3px solid #709FB0;
}
QPushButton#primary:hover {
    background-color: #F1F7F8;
    border-color: #80A9B8;
    border-bottom-color: #527F91;
}
QPushButton#primary:pressed {
    background-color: #D9E9ED;
    border: 1px solid #729CAA;
    border-top: 3px solid #729CAA;
    border-bottom: 1px solid #729CAA;
    padding-top: 9px;
    padding-bottom: 5px;
}
QPushButton#primary:disabled {
    color: #9B949C;
    background-color: #F1F4F4;
    border: 1px solid #E2E7E8;
    border-bottom: 2px solid #D8DFE1;
}
QPushButton#danger {
    background-color: #FCF4F1;
    border: 1px solid #D9BFB9;
    border-bottom: 3px solid #CDA69D;
}
QPushButton#danger:hover {
    background-color: #FFF8F5;
    border-color: #C9A9A0;
    border-bottom-color: #B88E85;
}
QPushButton#danger:pressed {
    background-color: #F5E9E5;
    border: 1px solid #C5A49C;
    border-top: 3px solid #C5A49C;
    border-bottom: 1px solid #C5A49C;
    padding-top: 9px;
    padding-bottom: 5px;
}
QPushButton#danger:disabled {
    color: #9B949C;
    background-color: #F6F3F3;
    border: 1px solid #E2DBE0;
    border-bottom: 2px solid #D8D0D4;
}
"""
