noacli: the No Ampersand CLI shell

Dependencies
------------
This uses Python and Qt, which are depencies.  To install these:

Mac: (pick one)
  sudo pip3 install PyQt5
  pip3 install --user PyQt5

Ubuntu:
  sudo apt install python3-pyqt5

Philosophy
----------

There are lots of (old) traditional command line shells that are quite nice.
There are a few graphical shells that are nice (like gnome-shell, KDE, etc.)
Gnome shell even has a text interface (looking glass) that is nice, but
not very convenient for every day use.

This is a hybrid shell, with both cli and graphical features.
It is not a full turing complete parsed language, but it supports using
one underneath if you want that.   It doesn't even think about being a
full gui shell with integrated window manager either, it expects you to
have one, although it can help find or close lost windows.

The intent of this shell is to simplify a lot of cli things that make you
dedicate a terminal window to them and display their results in a more
convenient way made possible by using a full graphical interface instead
of a terminal window.

It's not that we hate background jobs, but that they seem silly when
you could have just opened another window.  It's not that we like a
proliferation of windows either -- this has measures to minimize that.

This shell tries to make the following concepts obsolete;
* terminal based text pagers
* background jobs
* waiting for jobs to complete before starting another
* terminal multiplexers
* terminal based scroll back buffers

None of these really make sense when you can just open another graphical window.

For example, instead of a command dumping a huge blob of text into a
terminal that scrolls away quickly and is lost, or piping that into a
pager, noacli will automatically put that text into a graphical window
that is sized to fit, has a scroll bar, and allows searching.  As the
program generates more output, the window will continue to collect it
and follow the end, similar to what tail -f does.

If you run another command, you get another window dedicated to it.

The graphical interface includes the following items as described below:
* Pull down menus
* Command edit window
* status message bar
* "qtail" independant large scrolling output window

The following dock windows can be rearranged, resized, and pulled off
the main window.  The view menu lets you bring back any of these if
they get lost.
* History dock window
* Job manager dock window
* Shortcut button dock
* Small output dock window
* log dock window 

The following settings dialog boxes allow editing settings:
* General settings editor
* Favorites editor
* Environment variable editor

# qtail #
The qtail window also works as a separate application from the shell,
functioning in a way similar to "tail -f" and taking a few similar
command line arguments.  As an external application, qtail will work
on files, growing files, and pipes.  It will automatically detect if a
file grows.

If qtail collects no output before the process exits, it will
automatically close.

A search box at the top of the window allows quickly finding text.
Pressing enter in the box will repeat the current search.  A counter
in the qtail status bar keeps track of repeated searches and notifies
if a search wraps to the start of the buffer.

By default, qtail starts reading a file 1M from the end, and only
remembers the most recent 10000 lines.  This is to preserve
performance and memory, but can be adjusted in settings.  Setting
either of these numbers to 0 allows infinite data kept.  (Use at your
own risk!)

# small output #
The small output dock window will collect output from commands that
output a small amount of text or no text and then exit quickly.  But
if a command outputs more, or you run another command before it
finishes, it gets transfered to the large scolling qtail window. 

If a command finishes and you run another command, normally the output
from the first is cleared, but you can check the 'keep' box if you
want to retain it for a short while (about two window fulls,
adjustable).  If you want to retain the output longer, press the dup
button to pop the output to a qtail window, whether not the process
has exited.

Programs that emit single lines and exit, or emit single lines slowly
will also have their output sent to the status bar at the bottom of
the main window.  Also, if the small output window is not visible when
a command sends output or exits, a notification will show in the
status bar temporarily. (Delay is settable.)

# history dock #
Like traditional cli shells, this shell keeps a history of your commands.
But unlike traditional shells, you view it in a graphical dock window
that is scrollable, sortable, and can be easily filtered.

Additionally, the history keeps track if commands you typed exited
successfully, got an error, or were never run at all.  The context
menu for the history window also lets you collapse dupcliate history
entries or trim the list to just unique command lines.  When duplicate
history lines are pruned, the history window keeps track of their use
frequency.  You can also right click on a history entry and choose to
save it favorites to mark it for future use.

You can also use ctrl-uparrow and ctrl-down in the command window to
browse the history.

# job manager #
The jobs you run are also tracked in a job manager dock window that
shows the critical job details and status, and helps you find or reopen lost 
windows.  Finished jobs with closed windows can be manually cleared or will
automatically clear after a timeout.

If you click on the window name in the job manager, it will raise the
window if there is one, and you can also rename the window.

Commands shown in both the job window and the history window can be
clicked on to copy them to the command edit window for further editing
or to run it again.  If you already had a partially typed command there,
it will be saved in history as a command that was never run.  Returning to
the unrun command will let you continue editing it.

# settings editor dialog #
All shell settings can be adjusted in a graphical settings edit window
that includes tooltips with default values and documentation for each
setting.  Numbers mentioned in this document are all settings and can
be changed.  An attempt has been made to make every major parameter
including timeouts and otherwise hardcoded values editable settings.
Settings with default values will have a grey background and will turn
to a white background when they are edited.

# favorites and button dock #

The favorites editor, when opened, shows your previuosly saved
favorites, your 10 most frequently run commands, and your 10 most
recent commands not already listed.  (These numbers are settings that
can be changed of course.)  You can check or uncheck the any entry if
you want to keep it or not.  Named entries show up in the button dock
for quick access.  Also, a shortcut key binding can be set for any
favorite.  A favorite can be flagged to be immediately run when
selected, or to be inserted into the edit window as a template for
further modification.  If the command contains a marker set to {} by
default), the cursor will be placed at the marker and the marker
selected.  Also, if there was something selected in the edit window
before selecting the favorite, it will replace the marker.

When editing favorites, duplicate commands, buttons, and shortcuts are
highlighted so you can fix them.  Duplicate commands are not allowed,
and all but the first will be deleted on save.

# main command edit #
The command edit box allows typing of commands.
Commands are not restricted to a single line, but can span multiple
lines.  Multi-line commands are fed (by default) directly to bash -c
which will run the command as if it was a normal multi-line shell
script.  Since commands can be multi-line, the enter key starts a new
line.  To actually run the command, use Ctrl-Enter, or press the run
button in the button dock.


If, for some reason, you need a list of files in a command, you can
press Ctrl-F to get a normal file browser window.  You can select
multiple files there and when "opened" the filenames will be inserted
into the command.  If you open the file browser with text immediately
before the cursor, it will treat that as a starting directory.  The
file browser is preconfigured with a number of default file groups.
The default list is editable in settings, or you can type a filter in
the command window, select it (with keyboard or mouse), and then press
Ctrl-F to override the default this once.  If you need to select a
directory instead of a file, highlight a single `/`

# Log dock window #

If you have a command that typically doesn't output anything
interesting, or all of its output is debug output (like, for instance,
a graphical program), then you can transfer its output to the log dock
(or start it there).  This window can collect output from mutliple
commands at once, and tags each line with the process ID and logs the
start and exit of jobs it is collecting from.  You can use the context
menu to manipulate the job associated with a particular log line or
clear the output from finished jobs.

Note that the log window is not designed for commands that have huge
amounts of output.  Use the qtail window for that.  By default, the
log window only remembers the last 10,000 lines from all processes it
is logging.

Menus
-----

The following pull down menus are also available:

The history menu shows the last 10 unique commands run.
Select one of them to re-edit it.

The job menu shows a quick status of recently run and currently
running jobs.  Select one to rase or open its window if there was one.

The view menu allows fast opening and closing of the various dock
windows.  Once visible, dock windows can be dragged, popped out,
popped back in, or closed by using their internal title bar and buttons.

The settings menu gives access to the settings dialog boxes, but also
allows you to save the window configurations by giving them a name, or
switch quickly to previously saved window configurations.

Suggested window configurations are "teeny minimal", "everything",
"output and buttons", and "default", but use your imagination to suit
your needs. If you have a default window profile, it will be loaded at
noacli start and saved at exit (unless you uncheck the DefWinProfile
setting).

Key bindings
------------

There are not many key bindings, although you can bind favorites to key bindings.

In addition to the editor key bindings used by Qt, the following keys are used:

While binding keys for favorites, binding a shortcut to Backspace will cancel it.
(This works around a bug / missing feature in Qt.)

Ctrl-Up     history up (doesn't work on mac)
Ctrl-P      history up
Ctrl-Down   history down (doesn't work on mac)
Ctrl-N 	    history down
Ctrl-Enter  run command in the command editor
Ctrl-Return run command in the command editor
Ctrl-F	    Invoke the file browser and insert the results into the editor

The history keys treat history as a ring, and the position is reset when
a command is run.

