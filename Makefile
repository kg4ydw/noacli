
UI= lib/qtail_ui.py lib/noacli_ui.py lib/settingsdialog_ui.py lib/tableviewer_ui.py lib/searchdock_ui.py
SRCFILES=$(shell git ls-files | grep -v gitignore)
DISTFILES=$(SRCFILES) $(UI) $(RESOURCES)

all: $(UI)

%.py: %.ui
	pyuic5 -o $@ $<

noacli.tgz: $(DISTFILES)
	rm -f noacli.tgz
	tar czvf noacli.tgz $(DISTFILES)

clean:
	rm *~ lib/*~ TAGS
clobber: clean
	rm -f noacli.tgz

tags: TAGS
TAGS: $(SRCFILES)
	etags --regex '/.*ETAGS: \(\w+\)/\1/' lib/datamodels.py lib/logoutput.py noacli.py lib/qtailbrowser.py qtail.py lib/smalloutput.py lib/typedqsettings.py lib/commandparser.py lib/envdatamodel.py lib/noajobs.py tableviewer.py lib/mydock.py lib/buttondock.py lib/favorites.py


# How much of brainstormed features are implemented? (this is a bit silly)
# key is in the top of documentation/nocli-ideas.txt
featureprogress:
	sed -n -e '/^----/,/^----/{ /^ *$$/d; /^.-/d; p}' documentation/noacli-ideas.txt  | cut -c 2|sort|uniq -c | awk '{p[$$2]=$$1; x+=$$1} END { for (i in p) { printf "%3d %4.1f %s\n",p[i],p[i]/x*100,i}; print x}'


# for emacs sometimes
# marger tags:
#  XX  possibly unfinished feature
#  XXX unfinished feature
#  XXXX very unfinished feature
#  XXXXX FIX ME NOW
#  DEBUG debug print
#  EXCEPT print if something unexpected went wrong
findprint:
	grep --color -nH -e 'print(' *.py lib/*.py |egrep -av 'DEBUG|EXCEPT'
findxx:
	grep --color -nH -e XX *.py lib/*.py 
findxxx:
	grep --color -nH -e XXX *.py lib/*.py 
findxxxx:
	grep --color -nH -e XXXX *.py lib/*.py 
findxxxxxx:
	grep --color -nH -e XXXXX *.py lib/*.py 
finddebug:
	grep --color -nH -e '^ *[^ #].*DEBUG' *.py lib/*.py 
