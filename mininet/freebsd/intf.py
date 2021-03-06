"""
A interface object that relies on ifconfig(8) to manipulate network
interfaces and devices.
"""
from mininet.baseintf import BaseIntf

class Intf( BaseIntf ):
    """Interface objects that use 'ifconfig' to configure the underlying
    interface that it represents"""

    def setMAC( self, macstr ):
        self.mac = macstr
        return ( self.ifconfig( 'down' ) +
                 self.ifconfig( 'ether', macstr, 'up' ) )

    def rename( self, newname ):
        "Rename interface"
        result = self.ifconfig( 'name', newname )
        self.name = newname
        return result

    def delete( self ):
        "Delete interface"
        jopt = '-vnet ' + self.node.jid if self.node.jid else ''
        self.ifconfig( jopt, 'destroy' )
        self.node.delIntf( self )
        self.link = None

    def status( self ):
        "Return intf status as a string"
        links, _err, _result = self.node.pexec( 'ifconfig -l' )
        if self.name in links:
            return "OK"
        else:
            return "MISSING"
