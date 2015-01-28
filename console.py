## console.py
# -*- coding: utf-8 -*-

import os
import cmd
import readline

banner ='''
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
   Version 0.2     |   @jjtibaquira
  ================================================
'''

class Console(cmd.Cmd):

  def __init__(self):
    cmd.Cmd.__init__(self)
    self.prompt = "nsearch> "
    self.intro  = '\033[0;36m'+banner+'\033[0m'  ## defaults to None
    self.doc_header = 'Nsearch Commands'
    self.misc_header = 'Nsearch Plugins'
    self.undoc_header = 'Other Commands'
    self.ruler = '='

  ## Command definitions ##
  def do_history(self, args):
    """Print a list of commands that have been entered"""
    print self._history

  def do_exit(self, args):
    """Exits from the console"""
    return -1

  ## Command definitions to support Cmd object functionality ##
  def do_EOF(self, args):
    """Exit on system end of file character"""
    return self.do_exit(args)

  def do_shell(self, args):
    """Pass command to a system shell when line begins with '!'"""
    os.system(args)

  def do_help(self, args):
    """Get help on commands
       'help' or '?' with no arguments prints a list of commands for which help is available
       'help <command>' or '? <command>' gives help on <command>
    """
    ## The only reason to define this method is for the help text in the doc string
    cmd.Cmd.do_help(self, args)

  ## Override methods in Cmd object ##
  def preloop(self):
    """Initialization before prompting user for commands.
       Despite the claims in the Cmd documentaion, Cmd.preloop() is not a stub.
    """
    cmd.Cmd.preloop(self)   ## sets up command completion
    self._history = []      ## No historyory yet
    self._locals  = {}      ## Initialize execution namespace for user
    self._globals = {}

  def postloop(self):
    """Take care of any unfinished business.
       Despite the claims in the Cmd documentaion, Cmd.postloop() is not a stub.
    """
    cmd.Cmd.postloop(self)   ## Clean up command completion
    print "Exiting..."

  def precmd(self, line):
    """ This method is called after the line has been input but before
        it has been interpreted. If you want to modifdy the input line
        before execution (for example, variable substitution) do it here.
    """
    self._history += [line.strip()]
    return line

  def postcmd(self, stop, line):
    """If you want to stop the console, return something that evaluates to true.
       If you want to do some post command processing, do it here.
    """
    return stop

  def emptyline(self):
    """Do nothing on empty input line"""
    pass

  def do_clear(self, args):
    """ Clear the shell """
    os.system("clear")
    print self.intro

  def do_banner(self, args):
    """ Display Banner """
    print('\033[0;36m'+banner+'\033[0m')

  def do_search(self, args):
    """ Search """
    if not args:
      help_search(self)
    else:
      if args.startswith('name:'):
        print "Buscar Script"
      elif args.startswith("category:"):
        print "Search by Category"
      else:
        print "Search all Scripts"

  def help_search(self):
    print '\n'.join([ "\n\tname     : Search by script's name",
      "\tcategory : Search by category",
      '\tUsage:',
      '\t\tsearch name:http',
      '\t\tsearch category:exploit',
      '\t\tsearch name:http category:exploit'])

  def default(self, line):
    """Called on an input line when the command prefix is not recognized.
       In that case we execute the line as Python code.
    """
    try:
        exec(line) in self._locals, self._globals
    except Exception, e:
        print e.__class__, ":", e