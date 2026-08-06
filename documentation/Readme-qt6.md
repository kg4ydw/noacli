
Early on in this project it was decided it was too soon to use Qt6 as it
didn't have support on all the desired platforms.  This will no longer be
true some time before April 2024.

In preparation for the change, the intent is that code will be ready for
the upgrade and only the imports will need to be adjusted.  The following
is a list of changes to make this true.


# Done

Deprecated exec_ --> exec

# Not done

Note that for class moves, most places in the code will just need the
import adjusted, but designer is notorious for fully qualifying every
class.

QtWidgets.QAction -> QtGui.Qaction

(hmm, that list was shorter than expected.)

# Code to remove

look for tag XXRemove

Python 3.8 (Ubuntu 20.04)
* noacli.pickfile code for lack of removeprefix

Qt 5.12 compatibility: 
* qtail.py QtTail.__init__ disable regex missing from QTextEdit

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
* Qt.Checked -> Qt.CheckState.Checked
* pyinstaller data files for resources
* QMouseEvent changes
* QDesktopWidget --> QScreen
* enhanced: QStringView
* new: QtDBus*
* new: QtWayland QtTextInputMethodManager
* some parts of QtWidgets -> QtGUI
* tools: QDoc
* wayland:
* QProcess::SeparateChannels / setReadChannel()