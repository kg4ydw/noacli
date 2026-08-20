
# fix bug in Qt 6.4.2 where pasting an empty buffer into QTextEditor segfaults
# this is not a python issue, C++ also crashes

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtGui import QClipboard
from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QApplication

class SafeClipboardFilter(QtCore.QObject):
  def __init__(self, editor):
      super().__init__()
      editor.installEventFilter(self)
  def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
    if isinstance(event, QtGui.QMouseEvent):
      if event.button() == QtCore.Qt.MouseButton.MiddleButton:
        # Middle click uses the 'Selection' clipboard mode on Linux
        if self.is_clipboard_invalid(QClipboard.Mode.Selection):
            return True
      #else:
      #    print("skip", event.button())
    #elif isinstance(event, QtGui.QMouseEvent):
    #    print(event, event.flags(), event.type(), event.button())
    # what else segfaults?
    #else:
    #    print("ACK ", type(event))
    return super().eventFilter(watched, event)

  def is_clipboard_invalid(self, mode: QClipboard.Mode) -> bool:
    """Returns True if the clipboard is dangerous and should be blocked."""
    clipboard = QtWidgets.QApplication.clipboard()
    mime_data = clipboard.mimeData(mode)

    # If the mime pointer is Null or contains zero valid formats, block it
    if mime_data is None or not mime_data.formats():
        # stuff something valid in the clipboard since blocking this event isn't enough
        QApplication.clipboard().setText("", mode)
        #print("block",mime_data, mime_data.formats())
        return True
    return False
