"""Shared Soft Outline visual tokens for Qt QSS and widgets."""

COLORS = {
    "canvas": "#FCFBF7",
    "ink": "#351F39",
    "border": "#C9BFCE",
    "hover_border": "#A99AB2",
    "focus": "#726A95",
    "selection": "#F0ECF4",
    "popup": "#FFFFFF",
    "disabled": "#9B949C",
}

COMBO_STYLE = """
QComboBox#softCombo {
    color: #351F39;
    background-color: #FFFFFF;
    border: 1px solid #C9BFCE;
    border-radius: 12px;
    padding: 7px 34px 7px 13px;
    min-height: 26px;
}
QComboBox#softCombo:hover {
    border: 1px solid #A99AB2;
    background-color: #FFFFFF;
}
QComboBox#softCombo:on {
    border: 1px solid #726A95;
    background-color: #F9F7FB;
}
QComboBox#softCombo:focus {
    border: 2px solid #726A95;
    padding-left: 12px;
    padding-right: 33px;
}
QComboBox#softCombo:disabled {
    color: #9B949C;
    background-color: #F6F3F3;
    border: 1px solid #E2DBE0;
}
QComboBox#softCombo::drop-down {
    border: none;
    background: transparent;
    width: 32px;
}
QComboBox#softCombo::down-arrow {
    image: none;
    width: 0px;
    height: 0px;
}
QComboBox#softCombo QAbstractItemView {
    color: #351F39;
    background-color: #FFFFFF;
    border: 1px solid #C9BFCE;
    border-radius: 12px;
    outline: none;
    padding: 4px;
    selection-background-color: #F0ECF4;
    selection-color: #351F39;
}
QComboBox#softCombo QAbstractItemView::item {
    border: none;
    min-height: 40px;
    padding: 0px;
}
"""
