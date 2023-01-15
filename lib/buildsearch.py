
__license__   = 'GPL v3'
__copyright__ = '2022, 2023, Steven Dick <kg4ydw@gmail.com>'

from PyQt5.QtCore import QRegularExpression as QRE

def buildSearch(text, ui):
    if not ui.actionUseRegEx.isChecked():
        return text  # plain text search
    opts = QRE.MultilineOption  # stuff always on
    if ui.actionCaseInsensitive.isChecked(): opts |= QRE.CaseInsensitiveOption
    if ui.actionUnicode.isChecked(): opts |= QRE.UseUnicodePropertiesOption
    re = QRE(text, opts)
    if not re.isValid():
        return None
    return re
