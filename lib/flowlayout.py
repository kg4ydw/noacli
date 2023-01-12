
# note: why isn't this included in the standard layouts???
# #mangled this to work with pyqt5 (just changed import)
# Then this was mangled to add button sorting

# Copyright (C) 2013 Riverbank Computing Limited.
# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause

"""PySide6 port of the widgets/layouts/flowlayout example from Qt v6.x"""

import sys, heapq

from PyQt5.QtCore import Qt, QMargins, QPoint, QRect, QSize
from PyQt5.QtWidgets import QApplication, QLayout, QPushButton, QSizePolicy, QWidget


class Window(QWidget):
    def __init__(self):
        super().__init__()

        flow_layout = FlowLayout(self)
        flow_layout.addWidget(QPushButton("Short"))
        flow_layout.addWidget(QPushButton("Longer"))
        flow_layout.addWidget(QPushButton("Different text"))
        flow_layout.addWidget(QPushButton("More text"))
        flow_layout.addWidget(QPushButton("Even longer button text"))

        self.setWindowTitle("Flow Layout")


class FlowLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(QMargins(0, 0, 0, 0))

        self._item_list = []
        self.mode = 0

    def unsorted(self):
        self.mode = 0

    def alphasort(self):
        self._item_list = sorted(self._item_list, key=lambda i: i.widget().objectName())
        oldmode = self.mode
        self.mode = 1
        if oldmode!=1: self.update()

    def greedy(self):
        oldmode = self.mode
        self.mode = 2
        if oldmode!=2: self.update()

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]

        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def _do_greedy_layout(self, rect, test_only):
        items = []
        for item in self._item_list:
            sh = item.sizeHint()
            items.append((sh.width(), sh.height(), item.widget().objectName(), item))
        items = sorted(items, reverse=True)
        smallest = items[-1][0]
        
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()
        greedy = []
        #print(rect, rect.x(), rect.right(), rect.right()-rect.x()) # DEBUG

        while items:
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(
                QSizePolicy.ToolButton, QSizePolicy.ToolButton, Qt.Horizontal
            )
            layout_spacing_y = style.layoutSpacing(
                QSizePolicy.ToolButton, QSizePolicy.ToolButton, Qt.Vertical
            )
            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y
            room = rect.right() - x
            if room<smallest:
                i = len(items)
            else:
                for i in range(len(items)):
                    # print('x={} y={} room={} w[{}]={}'.format(x,y,room, i,items[i][0])) # DEBUG
                    if items[i][0] < room:
                        break
            if i>=len(items) or room<smallest:
                # if len(items)>1: print('wrap room={}<{} / {} {}'.format(room, smallest, items[0][0], items[1][0])) # DEBUG
                # nothing fits, insert the top item on next line
                i=0
                it = items.pop(0)
                item = it[3]
                greedy.append(item)
                x = rect.x()
                if line_height>0:
                    y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            else:
                it = items.pop(i)
                item = it[3]
                greedy.append(item)
                next_x = x + item.sizeHint().width() + space_x
            # print('place {}={},{} at {}-{},{}'.format(i, it[0], it[1], x, next_x, y)) # DEBUG
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        if not test_only:
            self._item_list = greedy
        return y + line_height - rect.y()
    

    def _do_layout(self, rect, test_only):
        if self.mode==1: self.alphasort()
        elif self.mode==2: return self._do_greedy_layout(rect, test_only)
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(
                QSizePolicy.ToolButton, QSizePolicy.ToolButton, Qt.Horizontal
            )
            layout_spacing_y = style.layoutSpacing(
                QSizePolicy.ToolButton, QSizePolicy.ToolButton, Qt.Vertical
            )
            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = Window()
    main_win.show()
    sys.exit(app.exec())
