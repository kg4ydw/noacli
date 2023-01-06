from PyQt5.QtCore import QRegularExpression as QRE

def buildSearch(text, ui):
    if not ui.actionUseRegEx.isChecked():
        return text  # plain text search
    opts = QRE.MultilineOption  # stuff always on
    if ui.actionCaseInsensitive.isChecked(): opts |= QRE.CaseInsensitiveOption
    if ui.actionUnicode.isChecked(): opts |= QRE.UseUnicodePropertiesOption
    return QRE(text, opts)
