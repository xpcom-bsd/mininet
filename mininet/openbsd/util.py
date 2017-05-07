"""
OS-specific utility functions for OpenBSD, counterpart to util.py.
"""

from mininet.log import output, error, warn, debug
from resource import getrlimit, setrlimit, RLIMIT_NPROC, RLIMIT_NOFILE
from mininet.util import ( quietRun, retry )


LO='lo0'                       # loopback name.
DP_MODE=None                   # no OVS (unless manually built?) 

# Interface management
#
# Interfaces are managed as strings which are simply the
# interface names, of the form 'nodeN-ethM'.
#
# To connect nodes, we create virtual ethernet pairs (epairs), and then place
# them in the pair of nodes that we want to communicate. We then update the
# node's list of interfaces and connectivity map.
#

def makeIntfPair( intf1, intf2, addr1=None, addr2=None, node1=None, node2=None,
                  deleteIntfs=True, runCmd=None ):
    """Make two patched pair(4)s connnecting new interfaces intf1 and intf2
       intf1: name for interface 1
       intf2: name for interface 2
       addr1: MAC address for interface 1 (optional)
       addr2: MAC address for interface 2 (optional)
       node1: home node for interface 1 (optional)
       node2: home node for interface 2 (optional)
       deleteIntfs: delete intfs before creating them
       runCmd: function to run shell commands (quietRun)
       raises Exception on failure"""
    if not runCmd:
        runCmd = quietRun
    if deleteIntfs:
        # Delete any old interfaces with the same names - want intf-node map?
        quietRun( deleteCmd( intf1, node1 ) )
        quietRun( deleteCmd( intf2, node2 ) )
    # Create new pair(4)s
    out = quietRun( 'ifconfig pair' + Intf.next() + ' create' )
    out = quietRun( 'ifconfig pair' + Intf.next() + ' create' )

    # doas ifconfig pair4 create lladdr fe:e1:ba:d4:ee:58 rdomain 1 up
    quietRun( 'ifconfig %s link %s name %s' % ( end1, addr1, intf1 ) )
    quietRun( 'ifconfig %s link %s name %s' % ( end2, addr2, intf2 ) )

    # Move interfaces if necessary i.e. ends are specified
    if node1 and node1.rdomain:
        out1 = moveIntfNoRetry( intf1, node1 )
        if not ( out1 ):
            raise Exception( 'Failed to move %s to %s', intf1, node1 )
    if node2 and node2.rdomain:
        out2 = moveIntfNoRetry( intf2, node2 )
        if not ( out2 ):
            raise Exception( 'Failed to move %s to %s', intf2, node2 )

def deleteCmd( intf, node=None ):
    """Command to destroy an interface. If only intf is specified, assume that
       it's in the host."""
    return 'ifconfig %s %s destroy' % ( intf, opts if opts else '' )

def moveIntfNoRetry( intf, dstNode, printError=False ):
    """Move interface to node from host/root space, without retrying.
       intf: string, interface
        dstNode: destination Node
        printError: if true, print error"""
    intf = str( intf )
    cmd = 'ifconfig %s vnet %s' % ( intf, dstNode.jid )
    cmdOutput = quietRun( cmd )
    # If command does not produce any output, then we can assume
    # that the interface has been moved successfully.
    if cmdOutput:
        if printError:
            error( '*** Error: moveIntf: ' + intf +
                   ' not successfully moved to ' + dstNode.name + ':\n',
                   cmdOutput )
        return False
    return True

# duplicated in other platforms
def moveIntf( intf, dstNode, printError=True,
              retries=3, delaySecs=0.001 ):
    """Move interface to node, retrying on failure.
       intf: string, interface
       dstNode: destination Node
       printError: if true, print error"""
    retry( retries, delaySecs, moveIntfNoRetry, intf, dstNode,
           printError=printError )

# Other stuff we use
def sysctlTestAndSet( name, limit ):
    "Helper function to set sysctl limits"
    oldLimit = quietRun( 'sysctl -n ' + name )
    if 'sysctl' in oldLimit:
        error( 'Could not set value: %s' % out )
        return
    if isinstance( limit, int ):
        #compare integer limits before overriding
        if int( oldLimit ) < limit:
            quietRun( 'sysctl %s=%s' % name, limit )
    else:
        #overwrite non-integer limits
        quietRun( 'sysctl %s=%s' % name, limit )

def rlimitTestAndSet( name, limit ):
    "Helper function to set rlimits"
    soft, hard = getrlimit( name )
    if soft < limit:
        hardLimit = hard if limit < hard else limit
        setrlimit( name, ( limit, hardLimit ) )

def fixLimits():
    "Fix ridiculously small resource limits."
    # see what needs to be/should be tuned here
    pass
    #debug( "*** Setting resource limits\n" )
    #try:
        #rlimitTestAndSet( RLIMIT_NPROC, 8192 )
        #rlimitTestAndSet( RLIMIT_NOFILE, 16384 )
        #Increase open file limit
        #sysctlTestAndSet( 'kern.maxfiles', 10000 )
        #Increase network buffer space
        #sysctlTestAndSet( 'net.core.wmem_max', 16777216 )
        #sysctlTestAndSet( 'net.core.rmem_max', 16777216 )
        #sysctlTestAndSet( 'net.ipv4.tcp_rmem', '10240 87380 16777216' )
        #sysctlTestAndSet( 'net.ipv4.tcp_wmem', '10240 87380 16777216' )
        #sysctlTestAndSet( 'net.core.netdev_max_backlog', 5000 )
        #Increase arp cache size
        #sysctlTestAndSet( 'net.ipv4.neigh.default.gc_thresh1', 4096 )
        #sysctlTestAndSet( 'net.ipv4.neigh.default.gc_thresh2', 8192 )
        #sysctlTestAndSet( 'net.ipv4.neigh.default.gc_thresh3', 16384 )
        #Increase routing table size
        #sysctlTestAndSet( 'net.ipv4.route.max_size', 32768 )
        #Increase number of PTYs for nodes
        #sysctlTestAndSet( 'kernel.pty.max', 20000 )
    # pylint: disable=broad-except
    #except Exception:
        #warn( "*** Error setting resource limits. "
        #      "Mininet's performance may be affected.\n" )
    # pylint: enable=broad-except

def numCores():
    "Returns number of CPU cores based on /proc/cpuinfo"
    if hasattr( numCores, 'ncores' ):
        return numCores.ncores
    try:
        numCores.ncores = int( quietRun('sysctl -n hw.ncpu') )
    except ValueError:
        return 0
    return numCores.ncores

# Kernel module manipulation
# we don't have any.

def lsmod():
    """Return list of currently loaded kernel modules."""
    pass

def rmmod( mod ):
    """Attempt to unload a specified module.
       mod: module string"""
    pass

def modprobe( mod ):
    """Attempt to load a specified module.
       mod: module string"""
    pass
