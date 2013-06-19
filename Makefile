BASEURL=http://natlang.cs.sfu.ca/
LIVEDIR=/net/local-adhara/gn-data/htdocs/fas/sites/natlang/
LOCALDIR=$(PWD)/_local

# Build locally.
all:
	jekyll build --base-url="$(BASEURL)"

# Install to the live site.
install: all
	rsync --recursive --delete _site/ "$(LIVEDIR)"
	chgrp -R natlang "$(LIVEDIR)"
	chmod g+rw "$(LIVEDIR)"
	find "$(LIVEDIR)" -type d -exec chmod g+x {} \;

# Build locally with the base-url set for testing. Don't copy to the live site from here.
local:
	echo "baseurl: file://$(LOCALDIR)/" > _localconfig.yml
	cat _config.yml >> _localconfig.yml
	jekyll build --config _localconfig.yml -d $(LOCALDIR) 

clean:
	rm -rf _site
