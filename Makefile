BASEURL=http://natlang.cs.sfu.ca/
LIVEDIR=/net/local-adhara/gn-data/htdocs/fas/sites/natlang/

all:
	jekyll --base-url="$(BASEURL)"

install: all
	rsync --recursive --delete _site/ "$(LIVEDIR)"

clean:
	rm -rf _site
