![noacli](../icons/noacli.png "icon")
noacli: the No Ampersand CLI shell

This shell does most things regular CLI shells do (except full parsing
and Turing complete programming), but in a graphical interface.
Noacli takes full advantage of having a GUI as much as possible,
including common trivial data visualization stuff.

This readme is not comprehensive, but it hits the major points.
There's more stuff discoverable in the shell.

# = Dependencies

This uses Python and Qt, which are dependencies.  To install these:

Mac: (pick one)
* sudo pip3 install PyQt5
* pip3 install --user PyQt5

Ubuntu:
* sudo apt install python3-pyqt5

This has been tested with Python 3.8 - 3.10 and Qt 5.12 - 5.15.
(Note: Qt before 5.13 will be missing some functionality.)

# = Philosophy

There are lots of (old) traditional command line shells that are quite nice.
There are a few graphical shells that are nice (like gnome-shell, KDE, etc.)
Gnome shell even has a text interface (looking glass) that is nice, but
not very convenient for every day use.

This is a hybrid shell, with both cli and graphical features.
It is not a full Turing complete parsed language, but it fully
supports using one underneath if you want that.  It doesn't even think
about being a full GUI shell with integrated window manager either, it
expects you to have one, although it can help find or close lost
windows.

The intent of this shell is to simplify a lot of cli things that make you
dedicate a terminal window to them and display their results in a more
convenient way made possible by using a full graphical interface instead
of a terminal window.

It's not that we hate background jobs, but that they seem silly when
you could have just opened another window.  It's not that we like a
proliferation of windows either -- this has measures to minimize that.

This shell tries to make the following concepts obsolete:
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

# = Structure and details

The graphical interface includes the following items as described below:
* Pull down menus
* Command edit window
* status message bar
* "qtail" independent large scrolling output window
* Table viewer (makes up for proportional fonts and removes the need for 80 column fixed text)

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
* Button dock editor

## == qtail
The qtail window also works as a separate application from the shell,
functioning in a way similar to "tail -f" and taking a few similar
command line arguments.  As an external application, qtail will work
on files, growing files, and pipes.

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

If you have a file that is being rewritten from the start or a command
you want to periodically rerun, you can use options in the watch menu
(or the`--autorefresh` option, below) to get updates on demand or time
interval, similar to the cli watch command.

By default, within the shell, qtail is followed by possible options
and a command.  There is no space between the option and its
parameter.  Options are either a single dash followed by a single
letter and possibly a parameter, or a double dash followed by an
option word and possibly and equal sign (=) and the parameter.

Within the shell, the table command takes the `--file` and `--files` options
to indicate the following are filenames rather than a command.

Qtail supports the following options:

`--file`  
    After all options will be a single filename (spaces and all)

`--files`  
    After all the options will be a space separated list of filenames, each of which will be opened in its own qtail window
    
'--font'
    Choose the primary or secondary font (1 or 2) instead of the default font (only works from inside noacli), or specify a font by name, e.g., --font=mono

`--nowrap`  
    Turn word wrap off initially (may be faster)

`--autorefresh` or `--autorefresh=seconds`  
    Enable autorefresh and (optionally) set refresh interval

`--bytes=N`  
    Set size of initial tail backtrack, default=1M

`--whole`  
    Read whole file at start.  WARNING: may be slow and/or exhaust memory.

`--title=`  
    Set window title instead of using command or filename.

`--format=` (plain html markdown)  
    Set the file format; default is plain.  Warning: markdown must read the entire file at once.

`--url`  
    Treat filename as a URL, autodetect format.  Note: doesn't work with remote urls

`--autorefresh`  or `--autorefresh=seconds`  
    Enable autorefresh (default = 30 seconds); only works on files outside noacli; in noacli,  commands will rerun like "watch"

`--watch`  
   Check the 'watch' checkbox which adjusts the default button action


## == table viewer

The table viewer takes the output from a command and tries to parse it
as a table, using several heuristics to try to guess where the columns are.
If the heuristic doesn't guess right, you can give it hints with the
following options:

 `--skip=`  
    skip lines preceding the table (default=0)

 `--delimiters=`  or `--delimiter=`  
    specify single characters that could be delimiters.  Default is comma, pipe, tab colon ('|\t,:')
    
 `--gap=`  
    Minimum number of spaces between columns if it is space delimited;
    defaults to 2 or if headers are underlined (with = or -) then 1
    
 `--columns=` or `--cols`  
    If the fixed width parser can't guess column boundaries,
    you can specify them (comma separated) If the heuristic gets it
    almost right, use the item in the view menu to copy the offsets to
    the clipboard, edit them, and try again with this option.
    
 `--headers=`  
    comma separated headers to use instead of the first line
    
`--fixed`  
    force fixed width parsing instead of csv parsing with delimiters

`--mask` or `--mask=nlines`  
    Forces --fixed; Read the whole table (or just nlines) up front and use a mask algorithm to split fixed width tables, looking for columns with only whitespace (or delimiters if specified, e.g. --delimiters=-=+: ) and merge in any extra columns with --columns= (negative values to remove column seperations)


The following options change defaults that can be changed in the GUI.
These are especially useful in favorites.


`--filtercol=` and `--filter=`  
    Set initial filter column and filter string (useful in favorites)
    Filtercol may be a (1 based) column index or the first match in headers

 `--noheader`  
    There is no header in the data, use numbered headers instead of the first line

`--nopick`  `--pick`  
    Don't show (or show) the colum picker at start (default: show if more than 10 columns)


Like qtail, table also accepts the --file and --files options when used inside noacli.

By default the search box in the column picker searches the entire
table, but if you select a single column name from the list and press
return in the search box, searches will be restricted to that column.
Unselect all columns and press return to search the entire table again.

## == small output
The small output dock window will collect output from commands that
output a small amount of text or no text and then exit quickly.  But
if a command outputs more, or you run another command before it
finishes, it gets transferred to the large scrolling qtail window. 

If a command finishes and you run another command, normally the output
from the first is cleared, but you can check the 'keep' box if you
want to retain it for a short while (about two window fulls,
adjustable).  If you want to retain the output longer, press the dup
button to pop the output to a qtail window, whether or not the process
has exited.

Programs that emit single lines and exit, or emit single lines slowly
 will also have their output sent to the status bar at the bottom of
the main window.  Also, if the small output window is not visible when
a command sends output or exits, a notification will show in the
status bar temporarily. (Delay is settable.)

## == history dock
Like traditional cli shells, this shell keeps a history of your commands.
But unlike traditional shells, you view it in a graphical dock window
that is scrollable, sortable, and can be easily filtered.

Additionally, the history keeps track if commands you typed exited
successfully, got an error, or were never run at all.  The context
menu for the history window also lets you collapse duplicate history
entries or trim the list to just unique command lines.  When duplicate
history lines are pruned, the history window keeps track of their use
frequency.  You can also right click on a history entry and choose to
save it favorites to mark it for future use.

You can also use ctrl-uparrow and ctrl-down in the command window to
browse the history.

## == job manager

The jobs you run are also tracked in a job manager dock window that
shows the critical job details and status, and helps you find or
reopen lost windows.  Finished jobs with closed windows can be
manually cleared or will automatically clear after a timeout.

If you double click on the window name or mode in the job manager, it
will raise the window if there is one and move the mouse to it, and
you can also rename the window by editing its name in the window column.

Commands shown in both the job window and the history window can be
clicked on to copy them to the command edit window for further editing
or to run it again.  If you already had a partially typed command there,
it will be saved in history as a command that was never run.  Returning to
the unrun command will let you continue editing it.

## == settings editor dialog
All shell settings can be adjusted in a graphical settings edit window
that includes tooltips with default values and documentation for each
setting.  Numbers mentioned in this document are all settings and can
be changed.  An attempt has been made to make every major parameter
including timeouts and otherwise hard coded values editable settings.
Settings with default values will have a grey background and will turn
to a white background when they are edited.

## == favorites and button docks

The favorites editor, when opened, shows your previously saved
favorites, your 10 most recently run commands, and your 10 most
frequently run commands not already listed.  (These numbers are settings that
can be changed of course.)  You can check or uncheck 'keep' on an entry if
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

In settings, there is a button dock editor that allows creation of new
button docks and selecting which docks get which buttons, so that task
specific favorites can be grouped.  Newly named favorites are initially
added to the default button dock (which can be set from the context menu).

Named favorites not assigned to a dock will be assigned to the
(hidden) orphan dock on next shell start.  Empty docks will be
automatically deleted on next start.

Button order can be changed from the dock context menu, but this is
not (currently) savd.

## == main command edit
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
before the cursor, it will treat that as a starting directory.  If
there is a quote before the cursor, all the filenames chosen will be
quoted individually. The file browser is preconfigured with a number
of default file groups.  The default list is editable in settings, or
you can type a filter in the command window, select it (with keyboard
or mouse), and then press Ctrl-F to override the default this once.
If you need to select a directory instead of a file, highlight a
single `/`

If you want full pathnames instead of relative pathnames, type a * by
itself before the cursor (not selected) before activating Ctrl-F.

## == Log dock window

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

## == Output destinations

When commands are run, their output is sent to an initial destination.
The currently available output destinations are:

| keyword | destination
|----|-----|
| small | small output dock window
| qtail | large output browser
| log   | log dock window
| table | table parser and viewer

These output destinations are described above, but if the first word in a
command is one of the keywords (small log tail qtail) then the output
will be initially sent there, overriding any other defaults set.

Other possible special output targets may be added in the future.
Currently stdout and stderr are both sent to the same target, but in
the future, splitting them may be possible, although this can be done
now using traditional mechanisms available in the underlying wrapper
shell.

# = Wrappers

This shell does not have the programmability of typical command line
shells and only does extremely limited parsing.  Instead, it leans on
those older shells for that functionality.

So most command lines are wrapped in a command that does the actual
parsing and execution.  This is the wrapper.  Wrappers are named, and
there is a selectable default wrapper.  The initial default wrapper is
named bash (unless $SHELL is something different), which wraps
commands with [ 'bash', '-c' ].  The command itself is fed to this
wrapper unquoted and unmodified as the last argument.  Any quoting
will be interpreted by the shell in the wrapper.

A wrapper can also specify the default destination for its output,
although the user can override this on a per command basis.  (This is
set when the wrapper is created.)

The following sample wrappers are included by default:

    bash : (small) [ 'bash' , '-c' ]
    xterm : (log)  [ 'xterm' , '-e' ]
    gterm : (log)  [ 'gnome-terminal', '--', 'bash', '-c']


If your $SHELL is not one of these, a wrapper will be created,
This assumes  your shell accepts '-c' to run commands on the command line.

Note that gnome-terminal needs bash's help to continue parsing the command.

It is also possible to use ssh as a wrapper, sending the command to an
external host for parsing and execution.  A wrapper for each host
would be needed.

Wrappers can be trivially created on the fly with the addwrap command.
(An editor for wrappers may be added later.)

Note that wrappers are special in that the command buffer remnant is
passed to them directly without parsing.  If, for instance, your
wrapper is 'ssh', the command is passed to ssh as a single string with
unmolested quotes, spaces, return characters, pipes, etc., in it, and
ssh will pass that to the remote shell.  This is not the case if you
used ssh without a wrapper, and your default wrapper will interpret
these before running ssh, possibly locally.

# = Built in commands

(Numbers in () in the following paragraph are a count of bash built in commands.)

Noacli does not have many built in commands, as such commands are
usually needed to support scripting (0/19) which noacli doesn't
support.  Other commands are used to adjust shell settings
(4/9). manipulate jobs (3/8) and history (2/2), and environment
settings (6/13), which noacli does mostly with a graphical interface.

Having said that, there are a few things that need commands or work best
when embedded in the command line even if there is a graphical way to do it.

The following are the built in commands noacli has (so far).
These commands must be run by themselves, not combined with other commands.


`help`  
    list all of these and their description

`version`  
    show versions

`cd` or `chdir`  
    change local directory

`direct`  
    run without a wrapper using trivial parsing (space splitting only)

`addwrap`  
    add a new named wrapper

`setwrap`  
    set the default command wrapper

`type`  
    Find what things match the given command; shows both internal and
    external matches

The following builtins must be the first word of a regular command or addwrap command and change the default output destination:
  
`small` (default if none specified)  
    Send output to the small output dock window

`qtail` `tail` (small output overflow or by button)  
    View possibly growing output in a scrollable browser

`log` (small output button)  
    Merge output from this and other commands into the merged log dock window

`table`  
    Attempt to parse the output as a table; designed to handle
    delimited text, fixed width tables, and large numbers of columns.
    See options list above.


Additionally, wrappers are activated by keyword somewhat like builtin
commands and can be placed after the above output direction commands.

# = Buffering

Internally, noacli handles data in lines (which Qt calls paragraphs).
Otherwise, very little is done to control buffering, and this is
nearly completely in control of the subprocess and wrapping shell.
This is slightly complicated by noacli not using ptys (yet) to run
commands, but standard unix commands like `stdbuf` can control
buffering normally.

Except some programs (like python) completely ignore this and do their
own buffering anyway.  You can fix python by using `python -u` to run
unbuffered.  This might incur a performance penalty for large amounts
of output.  Otherwise, adding well placed flush() commands in your
code may help.

# = Menus

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

# = Key bindings

There are not many key bindings, although you can bind favorites to key bindings.

In addition to the editor key bindings used by Qt, the following keys are used:

While binding keys for favorites, binding a shortcut to Backspace will cancel it.
(This works around a bug / missing feature in Qt.)

|key         | function|
|---|---|
|Ctrl-Up     | history up (doesn't work on mac)
|Ctrl-P      | history up
|Ctrl-Down   | history down (doesn't work on mac)
|Ctrl-N      | history down
|Ctrl-Enter  | run command in the command editor
|Ctrl-Return | run command in the command editor
|Ctrl-F	     | Invoke the file browser and insert the results into the editor
|Alt-C	     | Move keyboard focus to command editor

The history keys treat history as a ring, and the position is reset when
a command is run.

In qtail:

|key         | function|
|---|---|
|Ctrl-F     | Moves keyboard focus to the find box

# = Odds and ends

Many items are internally documented with tooltips.
* The general settings editor shows a description of the option and
  the default value as tooltips for the two columns.
* Favorites buttons, history, and favorites display the full command as a tooltip

Built in commands are documented with the help command.

Tables windows will reset sort order and sizes when the top left
corner are clicked.  Double clicking on row and column headings will
resize the row to fit the contents if appropriate.

Clicking or double clicking on values in the table viewer copy the
contents to the clipboard.

Double clicking on the command in the history and jobs managers copies
it to the command edit window. (A partially edited command is saved to
history so it isn't lost.)

Many items have a context menu (right click) with additional actions.

If you close the main window, noacli will offer to also close other
windows opened in the session and kill any processes that were
started.  You can choose to ignore these left overs, but then noacli
can't exit until all of them exit on their own and will hang around
(without its own window) until then.  (This is a Qt limitation.)

## == Titles
Window titles, job names, and button names can all be edited.
You can force the default window title or name of a command by putting the title on the first line preceeded with a #

## == Using ssh as a wrapper

To use noacli with ssh to remote hosts, it needs to work without asking for
a password.  There are two ways to do this.

### === Permanent authorization
1) create a local ssh key (e.g, ssh-keygen -t rsa )
2) copy the public key to the remote host in the file `authorized_keys`
   (the permissions have to be exactly right for it to work, must not be
   group or world writable)
   The easiest way to do this is with `ssh-copy-id`
3) (optional) authorize this key with ssh-agent

### === Temporary authorization

On the local machine, edit `~/.ssh/config` and add the following lines

    ControlMaster auto
    ControlPath ~/.ssh/socket.%h.%p.%r
 
As above, neither the config file nor the .ssh directory can be group or
world writable, or ssh will ignore the files.

Then when you are ready to connect, authorize to the host once with
~~~
  ssh -fnN -O 'ControlPersist 2h' user@hostname
~~~
(Adjust time to your preference.)  This command makes a nice template button if you replace hostname with {} and you can check the link status with
~~~
  ssh -O check hostname
~~~  
cancel it with one of
* `ssh -O stop hostname`
* `ssh -O exit hostname`   (kills all existing connections too)

Note that the first command works well in an xterm wrapper to take
your password.

Once you have the above working, you can then add wrappers for each host with
something like
   ~~~   
   addwrap somehost ssh user@somehost.fqdn
   ~~~

## == Fonts

There are 3 fonts that can be adjusted:
* The font shared by the command editor, small output dock, and log dock
* The primary (default) font for qtail
* The secondary font (in menu) for qtail

There are three places to change the 3 adjustable fonts:
* All three are in General settings
* The main window settings menu "Editor font" lets you adjust the font of the command edit window (live) and applies that to the other two windows when you accept it (and saves it as a setting).
* In qtail, the view menu lets you change the font live, or switch to the primary or secondary font if those are set in general settings.

Note that font changes in general settings only affect new qtail windows and
that the font picker in qtail doesn't save its settings permanently.

## == Examples
### === favorites examples
These could be assigned to a button or a key binding.

* man page with table of contents (uncheck immediate checkbox)

        # man {}
        tail --findall=^[a-z][^[(]+$ -w --no-wrap man {}

* start (password authenticated) shared ssh session with remote host (see elsewhere for shared ssh connection set up); Uncheck the 'immediate' checkbox and fill in the hostname.

    xterm  h={} ; ssh -fnN -o 'ControlPersist 3h'  $h ; ssh -O check $h ; sleep 3

* check status of shared ssh connections

        # ssh status
        sh for i in ~/.ssh/socket.*  do
           j=${i/*socket./}
           h=${j/\.22*/}
           echo -n $h ' '  ssh -O check $h
        done


### === Wrapper examples

* default xterm wrapper, output goes to log

        log addwrap xterm xterm -e

* dc postfix calculator with 3 digits of precision (expression on command line, quotes not needed around '*')

        addwrap dc dc -e 3k -e

* run a command on remotehost via ssh

        addwrap remotehost ssh remotehost

# == Postscript

If you want to see where this project is going or want to influence it,
look at [Readme-feedback.md](documentation/Readme-feedback.md) and [noacli-ideas.txt](noacli-ideas.txt)

Until the end of 2022, new releases were daily.  As the shell matures,
this release frequency will decrease.  If you want new features,
please suggest them!! If you find bugs, (or documented bugs annoy
you), let us know!

This project (and this file) are Copyright (C) 2022, 2023, 2024 Steven Dick
and may be used under the terms of the GNU General Public LIcense v3
which should have been included with this project in the file license.txt
