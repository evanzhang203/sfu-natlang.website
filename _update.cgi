#!/usr/bin/env python2.6

import sys
import os
import shutil
import cgi
import cgitb
import json
import tempfile
import fcntl
import subprocess

# Path to the lock file.
lock_path = "/path/to/lockfile"
# Destination directory to synchronize to.
dest_path = "/path/to/webdir/"
# URL of the repository to pull from. For security reasons we fix this instead of reading it from the CGI request.
url = "https://github.com/some/repository"
# Path to directory to put log files in. Can be None to disable logging.
logs_path = "/path/to/logdir/"

class CommandFailed(Exception):
  pass

def call(argv):
  prog = subprocess.Popen(argv, stdin=None, stdout=sys.stdout, stderr=sys.stderr, close_fds=True)
  prog.wait()
  if prog.returncode != 0:
    raise CommandFailed

def mkdirp(path):
  try:
    os.makedirs(path)
  except os.error:
    pass

class EmptyLockFile(Exception):
  pass
class MalformedLockFile(Exception):
  pass
class CannotFindHead(Exception):
  pass

def parse_commit(string):
  return "%0x" % (int(string.strip(), 16))

def read_lock_file(file):
  lines = list(file)
  if len(lines) == 0:
    raise EmptyLockFile
  try:
    return parse_commit(lines[0])
  except ValueError:
    raise MalformedLockFile

def write_lock_file(file, commit):
  print >> file, commit

def is_ancestor(ancestor, descendant):
  """
  Check if one commit is the ancestor of another (both given by commit id) in the git repository at the current working directory.
  """
  argv = ["git", "rev-list", "--boundary", "%s..%s" % (ancestor, descendant)]
  prog = subprocess.Popen(argv, stdin=None, stdout=subprocess.PIPE, stderr=sys.stderr, close_fds=True)
  if len(list(prog.stdout)) == 0:
      return False
  else:
      return True

def get_head():
  """
  Get the commit id for the HEAD of the git repository at the current working directory.
  """
  prog = subprocess.Popen(["git", "rev-parse", "HEAD"], stdin=None, stdout=subprocess.PIPE, stderr=sys.stderr, close_fds=True)
  try:
    return parse_commit(prog.stdout.read())
  except:
    raise CannotFindHead

def build():
  """
  Executed in the checkout directory for the building step."
  """
  call(["make"])
def sync():
  """
  Executed in the checkout directory to update the destination from the checkout."
  """
  mkdirp(dest_path)
  # TODO: we probably want to add --delete for rsync, but then need to be careful about getting dest_path right and also not overwriting log files if they go in the same directory.
  call(["rsync", "--recursive", "_site/", dest_path])

def run(tmp_dir, email, commit):
  print >> sys.stderr, "update request from %s" % (email)
  print >> sys.stderr, "update is for commit %s" % (commit)

  # Do the checkout.
  call(["git", "clone", url, "checkout"])
  os.chdir("checkout")

  # Build in checkout directory.
  print >> sys.stderr, "building"
  try:
    build()
  except:
    print >> sys.stderr, "error: build failed"
    sys.exit(1)

  # Open the lock file in read mode. We will use this file descriptor for the lock, even though we may also open the file in write mode later.
  mkdirp(os.path.dirname(lock_path))
  open(lock_path, 'a').close() # Make sure the lock file exists
  lock_file_in = open(lock_path, 'r+')
  locked = False

  # Wait until we get the lock.
  fcntl.lockf(lock_file_in, fcntl.LOCK_EX)

  # Read the file to find out what commit the last update made was at. Die if it is newer than the current commit. The lock file should always be empty or contain the HEAD commit id for last update that successfully built and synchronized.
  try:
    last_commit = read_lock_file(lock_file_in)
    print >> sys.stderr, "the previous update was to commit %s" % (last_commit)
    if commit == last_commit or is_ancestor(commit, last_commit):
      print >> sys.stderr, "our commit is not newer than the previous update, stopping"
      sys.exit(0)
    else:
      print >> sys.stderr, "our commit is newer than the previous update, continuing"
  except EmptyLockFile:
    print >> sys.stderr, "lock file is empty, continuing"
  except MalformedLockFile:
    # Hopefully the lock file never becomes unreadable, but it if does then it seems best to continue so that we clean it up, even at the risk of overwriting updates at more recent commits.
    print >> sys.stderr, "warning: could not read the previous update information, continuing anyway"

  # Synchronize with destination.
  print >> sys.stderr, "synchronizing"
  try:
    sync()
  except:
    print >> sys.stderr, "error: synchronization failed"
    sys.exit(1)

  # Now we write the id for the latest commit from our update. There may have been more commits between when the update request was made and when we did the checkout, so we use the actual HEAD rather then the commit from the payload. If we can't get the head then something is seriously wrong and we leave the lock file as it was and hope that some future update will fix things for us.
  ok = False
  try:
    head_commit = get_head()
    ok = True
  except IndexError:
    print >> sys.stderr, "warning: could not get the HEAD of the repository, leaving the lock file was it was"
  if ok:
    lock_file_out = open(lock_path, 'w')
    write_lock_file(lock_file_out, commit)
    lock_file_out.close()

  # Finally we can release the lock.
  print >> sys.stderr, "releasing lock"
  fcntl.lockf(lock_file_in, fcntl.LOCK_UN)
  lock_file_in.close()

cgitb.enable()

print "Content-type: text/plain"
print
print "starting"

form = cgi.FieldStorage()
payload = json.loads(form['payload'].value)
date = payload['repository']['pushed_at']
email = payload['pusher']['email']
commit = payload['head_commit']['id']

if logs_path is not None:
  mkdirp(logs_path)
  log_path = tempfile.mkdtemp(dir=logs_path, prefix="%s.%s." % (date, commit))
  log_out_file, log_err_file = [open(os.path.join(log_path, p), 'w') for p in ['stdout', 'stderr']]
  with open(os.path.join(log_path, "request"), 'w') as file:
    print >> file, json.dumps(payload, sort_keys=True, indent=2)

real_stdout, real_stderr = sys.stdout, sys.stderr
tmp_dir = tempfile.mkdtemp()
try:
  os.chdir(tmp_dir)
  if logs_path is not None:
    sys.stdout, sys.stderr = log_out_file, log_err_file
  run(tmp_dir, email, commit)
finally:
  shutil.rmtree(tmp_dir)
  if logs_path is not None:
    sys.stdout, sys.stderr = real_stdout, real_stderr
    log_out_file.close()
    log_err_file.close()

print "done"
