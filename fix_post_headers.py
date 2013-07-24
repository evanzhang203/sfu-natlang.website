
import os, sys, re, string, pprint

def parse_header(head_list):
    doc = {}
    current_key = None
    for line in head_list:
        m = re.match(r"^([^:]+):(.*)$", line)
        if line[0] == '-':
            doc[current_key] = string.strip(line)
        elif m is not None:
            key = m.group(1)
            doc[key] = string.strip(m.group(2))
            current_key = key
        else:
            doc[current_key] = string.strip(line)
    return doc

def split_file(f):
    doc = {}
    with open(f, 'r') as file:
        content = file.readlines()
        start_index = 0
        indices = [ i for i,x in enumerate(content) if re.match('---[ \t]*\n', x) ]
        if len(indices) > 2:
            raise ValueError("too many separators in file: %s" % (f))
        if len(indices) < 2:
            raise ValueError("too few separators in file: %s" % (f))
        header = content[indices[0]+1:indices[1]]
        rest = content[indices[1]+1:]
        doc = parse_header(header)
        doc['rest'] = ''.join(rest)
    return doc

def fix_post_headers():
    files = os.listdir('.')
    for f in files:
        filename = f.split('.')
        if len(filename) > 2:
            raise ValueError("filename has two dots: %s" % (f))
        if len(filename) < 2:
            continue
        (base, suf) = (filename[0], filename[1])
        if suf == 'markdown' or suf == 'md':
            doc = split_file(f)
            #pprint.pprint(doc)
            if 'layout' not in doc: 
                doc['layout'] = 'post'
            if 'title' not in doc: 
                doc['title'] = 'No title'
            output_lines = [ "---", "layout: " + doc['layout'], "title: " + doc["title"], "root: ../../", "---", doc['rest'] ]
            with open(f + ".new", "w") as out:
                out.write("\n".join(output_lines))

if __name__ == '__main__':
    fix_post_headers()
