
UI= qtail_ui.py noacli_ui.py settingsdialog_ui.py tableviewer_ui.py
SRCFILES=$(shell git ls-files | grep -v gitignore)
DISTFILES=$(SRCFILES) $(UI) $(RESOURCES)

all: $(UI)

%.py: %.ui
	pyuic5 -o $@ $<

tar: noacli.tgz

# special case, modify it to use flowlayout
noacli_ui.py: noacli_ui.ui
	pyuic5 -o noacli_ui.py noacli_ui.ui
	sed -i.bak '/buttonBox/s/QtWidgets.Q.BoxLayout/FlowLayout/' noacli_ui.py
	echo 'from flowlayout import FlowLayout' >> noacli_ui.py

noacli.tgz: $(DISTFILES)
	rm -f noacli.tgz
	tar czvf noacli.tgz $(DISTFILES)

clean:
	rm *~ TAGS
clobber: clean
	rm -f noacli.tgz

line100.pbm: line100-ascii.pbm
	convert line100-ascii.pbm line100.pbm

tags: TAGS
TAGS: $(SRCFILES)
	etags datamodels.py logoutput.py noacli.py qtailbrowser.py qtail.py smalloutput.py typedqsettings.py commandparser.py envdatamodel.py noajobs.py tableviewer.py 



# for emacs sometimes
# marger tags:
#  XX  possibly unfinished feature
#  XXX unfinished feature
#  XXXX very unfinished feature
#  XXXXX FIX ME NOW
#  DEBUG debug print
#  EXCEPT print if something unexpected went wrong
findprint:
	grep --color -nH -e print *.py|egrep -av 'DEBUG|EXCEPT'
findxx:
	grep --color -nH -e XX *.py
findxxx:
	grep --color -nH -e XXX *.py
findxxxx:
	grep --color -nH -e XXXX *.py
findxxxxxx:
	grep --color -nH -e XXXXX *.py
finddebug:
	grep --color -nH -e '^ *[^ #].*DEBUG' *.py
