"""
################################################################################
# Copyright (c) 2013, Ilgar Mashayev
# 
# Website: http://lazylabs.org
################################################################################
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

@author: ilgar
"""

import gobject
import gtk
import os
import subprocess

import terminatorlib.plugin as plugin
import terminatorlib.util as util
from terminatorlib.config import Config
from terminatorlib.container import Container
from terminatorlib.factory import Factory
from terminatorlib.terminal import Terminal
from terminatorlib.terminator import Terminator
from terminatorlib.util import dbg, err, gerr

AVAILABLE = ['ClonedSplittingMenu']

class ClonedSplittingMenu(plugin.MenuItem):
  capabilities = ['terminal_menu']
  config = Config()
  maker = Factory()

  def __init__(self):
    myconfig = self.config.plugin_get_config(self.__class__.__name__)
    # Now extract valid data from sections{}

  def callback(self, menuitems, menu, terminal):
    mhor = gtk.MenuItem('Clone Horizontally')
    mvert = gtk.MenuItem('Clone Vertically')

    mhor.connect('activate', self.clone_session, True, terminal)
    mvert.connect('activate', self.clone_session, False, terminal)

    menuitems.append(mhor)
    menuitems.append(mvert)

  def clone_session(self, menuitem, is_horizontal, terminal):
    container = self.get_terminal_container(terminal)
    if container:
      self.register_signals(container, terminal)

      cmd = self.get_terminal_cmd(terminal)
      cwd = terminal.terminator.pid_cwd(terminal.pid)

      sibling = ClonableTerminal()
      sibling.set_cwd(cwd)
      sibling.spawn_child_with_command(cmd)
      terminal.emit('split-horiz-clone' if is_horizontal else 'split-vert-clone', cwd, sibling)
    else:
      terminal.emit('split-horiz' if is_horizontal else 'split-vert', cwd)

  def get_terminal_container(self, terminal, container=None):
    terminator = Terminator()
    if not container:
      for window in terminator.windows:
        owner = self.get_terminal_container(terminal, window)
        if owner: return owner
    else:
      for child in container.get_children():
        if isinstance(child, Terminal) and child == terminal:
          return container
        if isinstance(child, Container):
          owner = self.get_terminal_container(terminal, child)
          if owner: return owner

  def register_signals(self, container, terminal):
    container.signals.append({
      'name': 'split-horiz-clone',
      'flags': gobject.SIGNAL_RUN_LAST,
      'return_type': gobject.TYPE_NONE,
      'param_types': (gobject.TYPE_STRING, gobject.TYPE_OBJECT)})

    container.signals.append({
      'name': 'split-vert-clone',
      'flags': gobject.SIGNAL_RUN_LAST,
      'return_type': gobject.TYPE_NONE,
      'param_types': (gobject.TYPE_STRING, gobject.TYPE_OBJECT)})

    container.register_signals(terminal)

    container.connect_child(terminal, 'split-horiz-clone', self.split_horiz)
    container.connect_child(terminal, 'split-vert-clone', self.split_vert)

  def split_horiz(self, terminal, cwd=None, sibling=None):
    container = self.get_terminal_container(terminal)
    return(container.split_axis(terminal, True, cwd, sibling))

  def split_vert(self, terminal, cwd=None, sibling=None):
    container = self.get_terminal_container(terminal)
    return(container.split_axis(terminal, False, cwd, sibling))

  def get_terminal_cmd(self, terminal):
    raw = subprocess.Popen(['ps', '--no-headers', '-p', str(terminal.pid), '-o', 'command'], stdout=subprocess.PIPE)
    ps_line = subprocess.check_output(['head', '-1'], stdin=raw.stdout).strip()
    if ps_line and ps_line.strip().startswith('ssh'):
      return ps_line.strip()

    raw = subprocess.Popen(['ps', '--no-headers', '--ppid', str(terminal.pid), '-o', 'command'], stdout=subprocess.PIPE)
    ps_lines = subprocess.check_output(['head', '-100'], stdin=raw.stdout).strip().split('\n')
    for ps_line in ps_lines:
      if ps_line.strip().startswith('ssh'):
        return ps_line.strip()

  def log(self, name, obj):
    with open('/tmp/log', 'a') as f:
      f.write('%s:' % name)
      f.write(str(obj))
      f.write(': done\n')


class ClonableTerminal(Terminal):
    def __init__(self):
        Terminal.__init__(self)

    def spawn_child_with_command(self, init_command=None, widget=None, respawn=False, debugserver=False):
        update_records = self.config['update_records']
        login = self.config['login_shell']
        args = []
        shell = None
        command = None

        if self.terminator.doing_layout == True:
            dbg('still laying out, refusing to spawn a child')
            return

        if respawn == False:
            self.vte.grab_focus()

        command = init_command

        options = self.config.options_get()
        if options and options.command:
            command = options.command
            options.command = None
        elif options and options.execute:
            command = options.execute
            options.execute = None
        elif self.config['use_custom_command']:
            command = self.config['custom_command']
        elif self.layout_command:
            command = self.layout_command
        elif debugserver is True:
            details = self.terminator.debug_address
            dbg('spawning debug session with: %s:%s' % (details[0],
                details[1]))
            command = 'telnet %s %s' % (details[0], details[1])

        if options and options.working_directory and options.working_directory != '':
            self.set_cwd(options.working_directory)
            options.working_directory = ''

        if type(command) is list:
            shell = util.path_lookup(command[0])
            args = command
        else:
            shell = util.shell_lookup()

            if self.config['login_shell']:
                args.insert(0, '-%s' % shell)
            else:
                args.insert(0, shell)

            if command is not None:
                args += ['-c', command]

        if shell is None:
            self.vte.feed(_('Unable to find a shell'))
            return(-1)

        try:
            os.putenv('WINDOWID', '%s' % self.vte.get_parent_window().xid)
        except AttributeError:
            pass

        envv = []
        envv.append('TERMINATOR_UUID=%s' % self.uuid.urn)
        if self.terminator.dbus_name:
            envv.append('TERMINATOR_DBUS_NAME=%s' % self.terminator.dbus_name)
        if self.terminator.dbus_path:
            envv.append('TERMINATOR_DBUS_PATH=%s' % self.terminator.dbus_path)

        dbg('Forking shell: "%s" with args: %s' % (shell, args))
        self.pid = self.vte.fork_command(command=shell, argv=args, envv=envv,
                                         loglastlog=login, 
                                         logwtmp=update_records,
                                         logutmp=update_records, 
                                         directory=self.cwd)
        self.command = shell

        self.titlebar.update()

        if self.pid == -1:
            self.vte.feed(_('Unable to start shell:') + shell)
            return(-1)

