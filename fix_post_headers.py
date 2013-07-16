
import os

def fix_post_headers():
    files = os.listdir('.')
    for f in files:
        filename = f.split('.')
        if len(filename) > 2:
            raise ValueError("filename has two dots: %s" % (f))
        (base, suf) = (filename[0], filename[1])
        if suf == 'markdown' or suf == 'md':
            print base, suf
            (layout, title) = read_header(f)

if __name__ == '__main__':
    fix_post_headers()
