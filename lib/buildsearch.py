
__license__   = 'GPL v3'
__copyright__ = '2022, 2023, 2026, Steven Dick <kg4ydw@gmail.com>'

from PyQt6.QtCore import QRegularExpression as QRE

def buildSearch(text, ui):
    if not ui.actionUseRegEx.isChecked():
        return text  # plain text search
    opts = QRE.PatternOption.MultilineOption  # stuff always on
    if ui.actionCaseInsensitive.isChecked(): opts |= QRE.PatternOption.CaseInsensitiveOption
    if ui.actionUnicode.isChecked(): opts |= QRE.PatternOption.UseUnicodePropertiesOption
    re = QRE(text, opts)
    if not re.isValid():
        return None
    return re
