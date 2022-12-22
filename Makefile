
UI= lib/qtail_ui.py lib/noacli_ui.py lib/settingsdialog_ui.py lib/tableviewer_ui.py
SRCFILES=$(shell git ls-files | grep -v gitignore)
DISTFILES=$(SRCFILES) $(UI) $(RESOURCES)

all: $(UI)

%.py: %.ui
	pyuic5 -o $@ $<

# special case, modify it to use flowlayout
lib/noacli_ui.py: lib/noacli_ui.ui
	pyuic5 -o lib/noacli_ui.py lib/noacli_ui.ui
	sed -i.bak '/buttonBox/s/QtWidgets.Q.BoxLayout/FlowLayout/' lib/noacli_ui.py
	echo 'from lib.flowlayout import FlowLayout' >> lib/noacli_ui.py

noacli.tgz: $(DISTFILES)
	rm -f noacli.tgz
	tar czvf noacli.tgz $(DISTFILES)

clean:
	rm *~ lib/*~ TAGS
clobber: clean
	rm -f noacli.tgz

tags: TAGS
TAGS: $(SRCFILES)
	etags --regex '/.*ETAGS: \(\w+\)/\1/' lib/datamodels.py lib/logoutput.py noacli.py lib/qtailbrowser.py qtail.py lib/smalloutput.py lib/typedqsettings.py lib/commandparser.py lib/envdatamodel.py lib/noajobs.py tableviewer.py lib/mydock.py



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
