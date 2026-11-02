## console.py

import cmd
import helper
import helpernmap
import i18n
import os
import sys

try:
  import readline
except ImportError:
  pass


banner = '\033[0;36m' + r'''
  ================================================
    _   _  _____  _____                     _
   | \ | |/  ___||  ___|                   | |
   |  \| |\ `--. | |__    __ _  _ __   ___ | |__
   | . ` | `--. \|  __|  / _` || '__| / __|| '_  |
   | |\  |/\__/ /| |___ | (_| || |   | (__ | | | |
   \_| \_/\____/ \____/  \__,_||_|    \___||_| |_|
  ================================================
    Version 0.4b  https://github.com/jtibaquira/nsearch  @jjtibaquira
    Email: jko@dragonjar.org  |   www.dragonjar.org
  ================================================
''' + '\033[0m'

class Console(cmd.Cmd):

  def __init__(self):
    cmd.Cmd.__init__(self)
    self.prompt = "nsearch> "
    self.intro  = banner
    self.doc_header = i18n.t("help.doc_header")
    self.misc_header = i18n.t("help.misc_header")
    self.undoc_header = i18n.t("help.undoc_header")
    self.ruler = '='

  ## Autocomplete definition list
  searchCommands = [ 'name', 'category', 'help', 'author']
  showfavOptions = ['name', 'ranking', 'help']

  ## Command definitions ##
  def do_history(self, args):
    """Print a list of commands that have been entered"""
    print(self._history)

  def do_exit(self, args):
    """Exit the console"""
    return -1

  def do_help(self, args):
    """Get help on commands
       'help' or '?' with no arguments prints a list of commands for which help is available
       'help <command>' or '? <command>' gives help on <command>
    """
    ## This method exists only to provide the help text in the docstring
    cmd.Cmd.do_help(self, args)

  ## Command definitions to support Cmd object functionality ##
  def do_EOF(self, args):
    """Exit on end of file"""
    return self.do_exit(args)

  ## Override methods in Cmd object ##
  def onecmd(self, line):
    """Report unexpected errors without closing the console."""
    try:
      return cmd.Cmd.onecmd(self, line)
    except Exception as e:
      print("Error: " + helper.sanitize(e))
      return False

  def preloop(self):
    """Initialization before prompting user for commands.
       Despite the claims in the Cmd documentation, Cmd.preloop() is not a stub.
    """
    cmd.Cmd.preloop(self)   ## sets up command completion
    self._history = ""      ## No history yet
    try:
      old_delims = readline.get_completer_delims()
      readline.set_completer_delims(old_delims.replace('-', ''))
    except NameError:
      pass

  def postloop(self):
    """Take care of any unfinished business.
       Despite the claims in the Cmd documentation, Cmd.postloop() is not a stub.
    """
    cmd.Cmd.postloop(self)   ## Clean up command completion
    print('\033[0;36m Closing NSEarch ... :D\033[0m')

  def precmd(self, line):
    """ This method is called after the line has been input but before
        it has been interpreted. If you want to modify the input line
        before execution (for example, variable substitution) do it here.
    """
    self._history += line.strip() + "\n"
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
    """ Clear the screen """
    helper.clearScreen()
    print(self.intro)

  def do_search(self, args):
    """ Search for scripts """
    search = helper.Helper(args,"search")
    search.process()

  def complete_search(self, text, line, begidx, endidx):
    if not text:
      commands = self.searchCommands[:]
    else:
      commands = [ f
                      for f in self.searchCommands
                      if f.startswith(text)
                  ]
    return commands

  def help_search(self):
    print('\n'.join([ "\n\tname     : " + i18n.t("help.help_fav_name") + "",
      "\tcategory : " + i18n.t("help.help_search_category") + "",
      "\tauthor   : " + i18n.t("help.help_search_author") + "",
      '\t' + i18n.t("help.help_usage") + ':',
      '\t\tsearch name:http',
      '\t\tsearch category:exploit',
      '\t\tsearch author:fyodor',
      '\t\tsearch name:http category:exploit author:fyodor']))

  def do_doc(self, args):
    """ Display the documentation of a script """
    doc = helper.Helper(args)
    doc.displayDoc()

  def help_doc(self):
    print("\t" + i18n.t("help.help_doc"))
    print("\t" + i18n.t("help.help_usage"))
    print("\t\t" + i18n.t("help.help_doc_exmp"))

  def complete_doc(self, text, line, begidx, endidx):
    """ Autocomplete over the last result """
    resultitems = helper.Helper()
    return [i for i in resultitems.resultitems() if i.startswith(text)]

  def do_last(self,args):
    """ Display the last results """
    helper.Helper().printlastResult()

  def help_last(self):
    print(i18n.t("help.help_last"))

  # Favorite actions
  def do_addfav(self,args):
    search = helper.Helper(args,"addfav")
    search.process()

  def help_addfav(self):
    print('\n'.join([
      "\t" + i18n.t("help.help_addfav") + "",
      "\tname     : " + i18n.t("help.help_fav_name") + "",
      "\tranking : " + i18n.t("help.help_fav_ranking") + "",
      '\t' + i18n.t("help.help_usage") + ':',
      '\t\taddfav name:http ranking:great']))

  def complete_addfav(self, text, line, begidx, endidx):
    """ Autocomplete over the last result """
    resultitems = helper.Helper()
    return [i for i in resultitems.resultitems() if i.startswith(text)]

  def do_delfav(self,args):
    search = helper.Helper(args,"delfav")
    search.process()

  def help_delfav(self):
    print('\n'.join([
      "\t" + i18n.t("help.help_delfav") + "",
      "\tname     : " + i18n.t("help.help_fav_name") + "",
      '\t' + i18n.t("help.help_usage") + ':',
      '\t\tdelfav name:http']))

  def complete_delfav(self, text, line, begidx, endidx):
    """ Autocomplete over the last result """
    resultitems = helper.Helper()
    return [i for i in resultitems.resultitems() if i.startswith(text)]

  def do_modfav(self,args):
    search = helper.Helper(args,"modfav")
    search.process()

  def help_modfav(self):
    print('\n'.join([
      "\t" + i18n.t("help.help_modfav") + "",
      "\tname     : " + i18n.t("help.help_fav_name") + "",
      "\tnewname : " + i18n.t("help.help_fav_name") + "",
      "\tnewranking   : " + i18n.t("help.help_fav_ranking") + "",
      '\t' + i18n.t("help.help_usage") + ':',
      '\t\tmodfav name:http newname:http-new-script newranking:super-great']))

  def complete_modfav(self, text, line, begidx, endidx):
    """ Autocomplete over the last result """
    resultitems = helper.Helper()
    return [i for i in resultitems.resultitems() if i.startswith(text)]

  def do_showfav(self,args):
    search = helper.Helper(args,"showfav")
    search.process()

  def help_showfav(self):
    print('\n'.join([
      "\t" + i18n.t("help.help_showfav") + "",
      "\tname     : " + i18n.t("help.help_fav_name") + "",
      "\tranking : " + i18n.t("help.help_fav_ranking") + "",
      '\t' + i18n.t("help.help_usage") + ':',
      '\t\tshowfav name:http',
      '\t\tshowfav ranking:great',
      '\t\tshowfav name:http ranking:great']))

  def complete_showfav(self, text, line, begidx, endidx):
    if not text:
      commands = self.showfavOptions[:]
    else:
      commands = [ f
                      for f in self.showfavOptions
                      if f.startswith(text)
                  ]
    return commands

  def do_run(self, args):
    ''' Command to run templates '''
    nmap = helpernmap.HelperNmap(args)
    nmap.process()

  def help_run(self):
    print('\n'.join([
      "\t" + i18n.t("help.help_run") + "",
      "\tnet     : " + i18n.t("help.help_run_net") + "",
      "\ttemplate : " + i18n.t("help.help_run_template") + "",
      '\t' + i18n.t("help.help_usage") + ':',
      '\t\trun template:http net:target']))


  def default(self, line):
    """Called when the command is not recognized."""
    print(i18n.t("help.help_unknown_command"))
