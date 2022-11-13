
UI= qtail_ui.py noacli_ui.py settingsdialog_ui.py
SRCFILES=$(shell git ls-files | grep -v gitignore)
DISTFILES=$(SRCFILES) qtail_ui.py

all: $(UI)

%.py: %.ui
	pyuic5 -o $@ $<

tar: noacli.tgz

# special case, modify it to use flowlayout
noacli_ui.py: noacli_ui.ui
	pyuic5 -o noacli_ui.py noacli_ui.ui
	sed -ie '/buttonBox/s/QtWidgets.Q.BoxLayout/FlowLayout/' noacli_ui.py
	echo 'from flowlayout import FlowLayout' >> noacli_ui.py

noacli.tgz: $(DISTFILES)
	rm -f noacli.tgz
	tar czvf noacli.tgz $(DISTFILES)

clean:
	rm *~ TAGS
clobber: clean
	rm -f noacli.tgz

# for emacs
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
