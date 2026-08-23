
noacli v1 used Qt5.

In 2026, some platforms have limited or poor support for Qt5, and Qt5
has issues with wayland.

The point of noacli v2 is to switch to Qt6.
As of the 2.0 version, this has been done, but it has caused bugs which are
being worked on.   In 2.1, new features will be added that take advantage
of Qt6 new features.

Currently testing with Qt 6.4 which has a few bugs but is what Ubuntu 24
ships with.

# Code to remove

look for tag XXRemove

Python 3.8 (Ubuntu 20.04, check MacOS)
* noacli.pickfile code for lack of removeprefix

Qt bug workaround, fixed in Qt 6.11+
  Docks prevent floating docks from being deleted by catching closeEvent
  * mydock.py
  * searchdock.py

# New features

Qt6 has new features that need to be explored and maybe old bugs fixed.
* Qt6 has features needed to function correctly in wayland
  some noacli 1.x features are broken because qt5 doesn't support wayland
* Qt6 has better regex group support? qtail can use this
  * show groups instead of prefix, regex, postfix ? (toggle between views?)

Speculation:
* tree widget was unusable in pyqt5, segfaults easily
* Maybe there is better support for link actions in files? lots of
  ideas in todo for this
* maybe (hope) the text widget family is better
* terminal/pty solution?

known: https://www.pythonguis.com/faq/pyqt5-vs-pyqt6/
* graphs module / regex group / apt protocol?  https://doc.qt.io/qt-6/qtgraphs-index.html
* port designer
* QRegExp -> QRegularExpression
* pyinstaller data files for resources
* QMouseEvent changes
* enhanced: QStringView
* new: QtDBus*
* QProcess::SeparateChannels / setReadChannel()