
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