Terminator plugins
==================

Clone session
-------------

Quite often we need to connect to our servers to view logs, etc. Typical usage pattern is to establish several sessions to the same server, tailing the logs on one of them, tweaking configs, checking something else at the same time on the other consoles.

I find Split window feature in Terminator useful, and what I was missing always is cloning current ssh session. When I have a remote console open and want to have connection to the same server from the same window, i.e. I do not want to have several windows, then arrange them on the display.

Good that Terminator is written in Python and can easily be extended with plugins. I had to spend some time reading source code of the Terminator to get an idea how it all works.

Installation is very simple:

    mkdir -p ~/.config/terminator/plugins
    cd ~/.config/terminator/plugins
    wget --no-check-certificate https://github.com/ilgarm/terminator_plugins/raw/master/clone_session.py

Then, restart Terminator, go to Preferences | Plugins, and select ClonedSplittingMenu plugin. With this plugin there will be two items added to the popup menu of Terminator: Clone Horizontally and Clone Vertically.

Plugin has a limitation at the moment, it expects that all ssh connections within the same Terminator window will be established to the same server. This is due to the way how I am trying to find current remote session: by getting child processes of current terminal process and checking if it is a ssh command. If there are any, it will just grab the first one.

For my use case, this limitation is not critical so far, so I did not spent time trying to fix that.

P.S. some useful information on writing Terminator plugins can be found [here](http://www.tenshu.net/2010/04/writing-terminator-plugins.html).

Let me know if there are any bugs found.
