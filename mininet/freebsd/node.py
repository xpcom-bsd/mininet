"""
Node: jail(2) based node. This currently requires a kernel capable of VIMAGE
resource virtualization.

Mininet 'hosts' are created by running shells within jails with network
virtualization (see vnet(9)). Links are created by epair(4)s.

This is a collection of helpers that call the right commands to manipulate these
components.
"""
import signal
from os import killpg

from subprocess import PIPE, Popen

from mininet.log import warn
from mininet.basenode import BaseNode
from mininet.util import quietRun

class Node( BaseNode ):
    """A virtual network node that manipulates and tracks jails."""

    def __init__( self, name, inNamespace=True, **params ):
        BaseNode.__init__( self, name, inNamespace, **params )

    def getShell( self, master, slave, mnopts=None ):
        """
        Starts a shell used by the node to run commands. If inNamespace=True,
        this is a two-stage process where a persistent vnet jail is started,
        then a shell is started within the jail. Otherwise it just starts a
        shell.
        """
        execcmd = 'mnexec'
        opts = '-cd' if mnopts is None else mnopts

        # -ci               : create, then output just the JID; 
        # vnet              : with virtual network stack; 
        # allow.raw_sockets : enable raw socket creation;
        # stop.timeout=0    : don't wait for a process to exit in a jail

        if self.inNamespace:
            cmd = [ 'jail', '-ci', 'vnet', 'allow.raw_sockets', 'persist',
                    'stop.timeout=0', 'name=mininet:' + self.name, 'path=/' ]
            ret = Popen( cmd, stdout=PIPE ).communicate()[ 0 ][ :-1 ]
            execcmd = 'jexec'
            opts = self.jid = ret
        else:
            self.jid = None

        # bash -i: force interactive
        # -s: pass $* to shell, and make process easy to find in ps outside of
        # a jail. prompt is set to sentinel chr( 127 )
        cmd = [ execcmd, opts, 'env', 'PS1=' + chr( 127 ),
                'bash', '--norc', '-is', 'mininet:' + self.name ]

        return Popen( cmd, stdin=slave, stdout=slave, stderr=slave,
                      close_fds=False )

    def mountPrivateDirs( self ):
        "mount private directories"
        # Avoid expanding a string into a list of chars
        assert not isinstance( self.privateDirs, basestring )
        for directory in self.privateDirs:
            if isinstance( directory, tuple ):
                # mount given private directory onto mountpoint
                mountPoint = directory[ 1 ] % self.__dict__
                privateDir = directory[ 0 ]
                diffDir = mountPoint + '_diff'
                quietRun( 'mkdir -p %s %s %s' %
                               ( privateDir, mountPoint, diffDir ) )
                quietRun( 'mount -t nullfs %s %s' % ( privateDir, mountPoint ) )
                quietRun( 'mount -t unionfs %s %s' % ( diffDir, mountPoint ) )
            else:
                # mount temporary filesystem on directory + name
                quietRun( 'mkdir -p %s' % directory + self.name )
                quietRun( 'mount -n -t tmpfs tmpfs %s' % directory + self.name )

    def unmountPrivateDirs( self ):
        "mount private directories -  overridden"
        for directory in self.privateDirs:
            # all ops are from prison0
            if isinstance( directory, tuple ):
                quietRun( 'umount %s' % directory[ 1 ] % self.__dict__ )
                quietRun( 'umount %s' % directory[ 1 ] % self.__dict__ )
            else:
                quietRun( 'umount %s' % directory + self.name )

    def terminate( self ):
        """
        Cleanup when node is killed. THis involves explicitly killing any
        processes in the jail, as stop.timeout seems to be ignored
        """
        self.unmountPrivateDirs()
        if self.jid:
            # for when stop.timeout=0 doesn't work
            quietRun( 'jexec ' + self.jid + ' pkill -9 bash' )
            quietRun( 'jail -r ' + self.jid )
        if self.shell:
            if self.shell.poll() is None:
                killpg( self.shell.pid, signal.SIGHUP )
        self.cleanup()

    def popen( self, *args, **kwargs ):
        """Return a Popen() object in our namespace
           args: Popen() args, single list, or string
           kwargs: Popen() keyword args"""
        defaults = { 'stdout': PIPE, 'stderr': PIPE,
                     'mncmd':
                     [ 'jexec', self.jid ] if self.jid else [ 'mnexec', '-d' ] }
        defaults.update( kwargs )
        if len( args ) == 1:
            if isinstance( args[ 0 ], list ):
                # popen([cmd, arg1, arg2...])
                cmd = args[ 0 ]
            elif isinstance( args[ 0 ], basestring ):
                # popen("cmd arg1 arg2...")
                cmd = args[ 0 ].split()
            else:
                raise Exception( 'popen() requires a string or list' )
        elif len( args ) > 0:
            # popen( cmd, arg1, arg2... )
            cmd = list( args )
        # Attach to our namespace  using mnexec -a
        cmd = defaults.pop( 'mncmd' ) + cmd
        # Shell requires a string, not a list!
        if defaults.get( 'shell', False ):
            cmd = ' '.join( cmd )
        popen = self._popen( cmd, **defaults )
        return popen

    def sendInt( self, intr=chr( 3 ) ):
        "Interrupt running command."
        quietRun( 'kill -2 %s' % self.lastPid )

    def setHostRoute( self, ip, intf ):
        """Add route to host.
           ip: IP address as dotted decimal
           intf: string, interface name
           intfs: interface map of names to Intf"""
        # add stronger checks for interface lookup
        self.cmd( 'route add -host %s %s' % ( ip, self.intfs( intf ).IP() ) )
     
    def setDefaultRoute( self, intf=None ):
        """Set the default route to go through intf.
           intf: Intf or {dev <intfname> via <gw-ip> ...}"""
        # Note setParam won't call us if intf is none
        if isinstance( intf, basestring ):
            argv = intf.split(' ')
            if 'via' not in argv[ 0 ]:
                warn( '%s: setDefaultRoute takes a port name but we got: %s\n' %
                      ( self.name, intf ) )
                return
            params = argv[ -1 ]
        else:
            params = intf.IP()
        self.cmd( 'route change default %s' % params )
