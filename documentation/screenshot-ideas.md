The following features are displayed in noacli-big-screenshot.png:

* tableviewer
  * column picker
  * hide columns
  * automatic csv parsing with , (for coax.csv)
  * automatic csv parsing with : (for /etc/passwd)
  * automatic fixed width parsing of ls -C
* qtail
  * search
  * search: find all
  * fancy hilights
  * search docks
  * ls with --nh ?
* noacli
  * history with exit values
  * commands that generated all windows shown
  * potential cluster command
  * complex bash programming in editor
  * buttons
  * extra button docks
  * reconfigurable docks

Staged commands
```
log echo test
addwrap cluster ssh cluster
table --nh ls -C
man man
table head /etc/passwd
cluster sacct -a -X -P
table --file coax.csv
table --mask -d:  --cols=73,-61 ss -l4p
```

The following features didn't fit, maybe additional images?

* tableviewer
  * fixed width mask parsing with hints (for ss)
  * filter by column contents
* qtail
  * watch menu??
  * syslog display?
