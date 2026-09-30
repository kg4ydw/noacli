![noacli](icons/noacli.png "icon")
[noacli](https://github.com/kg4ydw/noacli): the No Ampersand CLI shell

noacli is a hybrid graphical and command line interface shell.
It tries to use the command line interface where that is most efficient,
and graphical interface elements where that can be more efficient.

This is the short description.  For a a longer list of features, see
[documentation/Readme.md](documentation/Readme.md)

This shell does most things regular CLI shells do (except full parsing
and Turing complete programming), but in a graphical interface.
Noacli takes full advantage of having a GUI as much as possible,
including common trivial data visualization stuff.

This shell tries to make the following concepts obsolete:
* terminal based text pagers
* background jobs
* waiting for jobs to complete before starting another
* terminal multiplexers
* terminal based scroll back buffers

This does not replace the standard terminal shell, but augments it and
hopefully reduces your need to ever open a second terminal, as
everything not done in the first terminal window can be done in
noacli.  You would still want a traditional terminal window for
things like:

* Full screen text applications like vi, nethack
* Text based applications expecting input from the terminal
* Other programs expecting a terminal like sudo

![A busy screenshot](documentation/noacli-big-screenshot.png)

noacli includes three stand-alone but integrated programs:
* The main noacli shell window
* The qtail file viewer
* The tableviewer

The main shell window is a single command editor pane coupled with a
few pull down menus, some settings editors and a number of
rearrangable dock windows.

the docks are:
* The small output dock
* The history dock
* The job manager dock
* The combined log dock
* The favorites button dock

The settings editor dialog boxes are:
* General settings editor
* Favorites editor
* Environment variable editor
* Button dock editor
* Saved search editor

For a a longer list of features and details of the above features,
see [documentation/Readme.md](documentation/Readme.md)

The main window is composed of docks that can be rearranged and hidden, and
various configurations saved.  Here's some alternate configurations.

![Small](documentation/small-buttons.png "Small output and buttons")

[See more screenshots](documentation/screenshots.md)


The buttons in the button dock in these screenshots are user configurable
commands marked as favorites.


If you want to see where this project is going or want to influence it,
look at [Readme-feedback.md](documentation/Readme-feedback.md) and documentation/noacli-ideas.txt


The saved search editor allows creation of searches that automatically
run on output of matched commands.  This could be used to find, for
instance, interesting output in a frequently visited debug log, or to
build a table of contents from a structured text file, or to run
commands to view related documents.

For example, given these three searches:
* man headings: ^(\S|\S\s)+$
* man opts: ^\s*(-+\w+)
* man ref: (\S+)\(([0-9]\w*)\)

![Saved searches for man pages](documentation/saved-search-man.png)

The man headings will extract heading lines from the man page that do
not contain multiple consective spaces, run a find all search and display
the results.

The man options will similarly display the list of lines that look
like option descriptions.

The man ref line is set to not show the results, but instead highlight
the results, and also if a line is right clicked (as below), the group
results from the search can be used to fill in a template to generate
a commands to follow the references on the line.

![man manual page with references](documentation/man-man.png)
