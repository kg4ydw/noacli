If you are interested in where this project is going, I'm open to feedback!

The file noacli-ideas.txt is my road map, brainstorm list, and known
bug list.  You can browse that and let me know if there are
unimplemented features you want and I'll prioritize those.

You are also welcome to suggest things.  There's quite a few features
that I managed to implement before they ever got on that list, so
don't hesitate to suggest new ones.

Here are the items I currently need feedback for the most...

I'm open to code contributions also.  I'm trying to handle at least one
item from noacli-ideas.txt a day, so check with me to make sure we don't both
implement something on the same day.  (!!)

# Documentation

The documentation is probably too stream of consciousness.
Suggestions for reorganizing it are welcome.  (Maybe at least a TOC?)

Would people like videos of how this works?  (See documentation/video-scripts )

# More docks?

Right now, it opens lots of windows. But I could convert it to open
docks instead that could be combined into one window with tabbed panes
and side windows for qtail and tableviewer. (Or switch between these
modes, or have multiple main dock windows and switch between them.)
Would anyone use that? how should it work?  How would you specify you
want output to go to its own main window or a specific dock group?
Also, I should write a test app to see if I can make Qt crash when moving
docks between main windows.  (Qt docks seem to not be well debugged...)

Similarly,
multiple button docks are supported, but should other docks
also allow duplicates?
Should this support multiple command edit windows (rather than
just setting 'Always on visible workspace' or whatever your WM calls it)?
Each one might have its own dedicated small output and log windows, but
the job manager and history would need to be shared, although each history
dock could have a different viewing position.

# Key bindings?

Right now, you can assign key bindings to favorites, in addition to
and separately from the on screen buttons. Should I also add an
extended key binding editor for internal functions as well?
(In case the answer is yes, I have a list of such targets in ideas...)

# QTail search

Reverse search is currently not implemented.  How much is this missed, or
is it enough to be able to scroll back and see the highlight?  Does the
'find all' functionality replace reverse search?

# Installer?  Pypi?

Does this need a traditional python setup.py installer?

# Template madness

I've also mapped out a complex command templating system and variable
manager, but it started feeling like feature creep.  The idea would be to
have a dock of variables and regex rules, and when a regex rule matched
an output (or a typed command??), it would fill in a variable value.

Then you could include in your commands (especially ones from favorites)
things like {varname} or {{varname}} or {varname[0]} or {varname[-1]}
or {tablename[col][row]} or {tablename[col].avg} or{tablename[col].rand}
or something.  This would allow capturing of things like slurm job
numbers, process ID's, hostnames, etc., and using them in future
commands without needing to do copy/paste.

Or you could just use copy/paste and the existing single parameter
template fill-in.

# Man page explorer

I also mapped out a man page viewer with automatic linking, bread
crumb history, and guided browsing, faintly reminiscent of ancient
xman.

This would be an extension of the existing qtail, and some of the
features could be general enough to use anywhere.  The biggest man
specific feature would be recognizing man page hyperlinks as
pagename(sec) and looking for references in the See Also section and
incrementally building a tree of related pages.  I imagine that this
"tree" would get rearranged each time you switch pages to make the
current page the root (and it would have cycles).

There are other ideas for this to encourage exploration of random man
pages, like keeping a database of visited pages, suggesting an
unviewed page a day to read, etc.

# Resource limits, Process monitor, System monitor

The original design included some of the following...

A dialog box to edit ulimits...

Implementation of the 'times' command from shells; supported by python.

Grapical widgets to monitor process progress and/or resource consumption...
This turns out to not be supported by Qt or python, so the code to do
this would be highly unportable.  Also, if we add this, we could start
adding system monitors too, and eventually reimplement {,h,b,a}top in Qt
which is a project that is probably overdue to happen anyway...

# Other output formatters and visualizers

I had originally envisioned adding more formatters / viewers like
qtail and table viewer, but so far, I haven't come up with anything solid.

For example, a progress meter could be done, maybe using the
debconf-apt-progress protocol or maybe a regex scraper to pull numbers
out of an output stream and send them to matplotlib or something.  But
the debconf progress protocol seems like a pretty limited use case,
and anything involving matplotlib would be highly specialized unless
there's already a clever language to describe graphs.  (Hmm, maybe
make it easy to add a graph plugin and just do it in python?)

It might also be nice to have a visualizer for cpu and resource use
for running jobs.  But this is highly non-portable and Qt doesn't even
support proper collection of cpu usage stats from wait4, which is
mostly portable.  (Maybe time to rewrite QProcess to be more pythonic?)

# Remote stub

Before I fully explored ssh multiplexing, I considered writing a
remote stub to multiplex over ssh.  This would still be needed for
sudo support.  Other things this would help are remote environment
variable management, remote working directory tracking, and full
remote job management.

# Better ssh support

Once you have ssh multiplexing set up, the initial connection established,
and a wrapper set up, ssh through noacli works pretty well.

However, if your connection dies (intentionally or otherwise) and you
try ssh so that it asks for a password, the OS suspends noacli.
This can be mitigated by preceding ssh with the `setsid` command.

Management of multiple ssh connections and refreshing them would help.
For instance, instead of using `ssh -O check` to validate a
connection, just run the initial connection without `-f` and noacli
could watch for it to exit and add hooks in the wrapper to prompt to
revalidate it before running.

This would require some minimal terminal support in noacli while a
password is entered so that noacli can manage the ssh job afterwards.

# Terminal integration

Currently, noacli relies on existing external terminal applications if
you want to run quick commands like ssh validation.  (There are two
default wrappers for external terminals.)  If an integrated terminal
was used instead, noacli could better monitor the status of jobs run
in the terminal and might be able to switch a job from the small
output window to a terminal if it asked for input.  (This would
probably require rewriting QProcess, but that could fix other issues too.)

# Microsoft Windows support

noacli is untested in Windows, but there's not really a reason why it couldn't work.
There are a number of unportable things (like default wrappers) that might need
adjustment, and windows integrated ssh is missing features (like multiplexing?).

# Other misc.

Other minor features listed in noacli-ideas.txt that are notable but
not worth expanding on here:

* Sort tableview by number instead of string (convert type, add sort proxy)
* Multi-line editors for commands and stuff in various tables (context menu?) 
* Fancy environment variable editor (similar to above but domain specific)
* Table line spacing tweaks in all tables including tables in docks
* Manual Button dock arrangement (implement drag in FlowLayout)
* More button actions (middle and right click?)
* More options for fonts?  Save fonts in qtail?

Postscript
==========

The point of this file is to explicitly ask for feedback and
prioritizing implementation, so if any of the above sounds even faintly
interesting, let me know.  Some of the above will probably never get
implemented if I never get any feedback on it.