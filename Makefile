
UI= qtail_ui.py noacli_ui.py settingsdialog_ui.py
RESOURCES=noaclires.py qtailres.py 
SRCFILES=$(shell git ls-files | grep -v gitignore)
DISTFILES=$(SRCFILES) $(UI) $(RESOURCES)

all: $(UI) $(RESOURCES)

%.py: %.ui
	pyuic5 -o $@ $<

%.py: %.qrc
	rcc -g python -o $@ $<
# could probably build the qrc here too from dependency info

tar: noacli.tgz

# special case, modify it to use flowlayout
noacli_ui.py: noacli_ui.ui
	pyuic5 -o noacli_ui.py noacli_ui.ui
	sed -i.bak '/buttonBox/s/QtWidgets.Q.BoxLayout/FlowLayout/' noacli_ui.py
	echo 'from flowlayout import FlowLayout' >> noacli_ui.py

noacli.tgz: $(DISTFILES)
	rm -f noacli.tgz
	tar czvf noacli.tgz $(DISTFILES) $(RESOURCES)

clean:
	rm *~ TAGS
clobber: clean
	rm -f noacli.tgz

line100.pbm: line100-ascii.pbm
	convert line100-ascii.pbm line100.pbm

noaclires.py:: noacli.png
smalloutputres.py:: line.svg
qtailres.py:: qtail.png

tags: TAGS
TAGS: $(SRCFILES)
	etags datamodels.py logoutput.py noacli.py qtailbrowser.py qtail.py smalloutput.py typedqsettings.py


# can't use this?
noaclires.rcc: noacli-res.qrc line100.pbm  noacli.png  qtail.png
	rcc -binary -o noacli-res.rcc noacli-res.qrc

# for emacs sometimes
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
