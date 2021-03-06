#!/bin/sh

# Mininet install script with just the bits that are currently supported.
# It follows the logic/contents of `install.sh`.

dist=$(uname -s)
release=$(uname -r)

if [ "${dist}" = "OpenBSD" ]; then
    install='doas pkg_add -vI'
    remove='doas pkg_delete'
    pkginst=${install}
else
    printf '%s\n' "This version of the install script is for OpenBSD," \
                  "but you are using ${dist} - try running './configure'"
    exit 1
fi

# Get directory containing mininet folder
MININET_DIR=$( CDPATH= cd -- "$( dirname -- "$0" )/../.." && pwd -P )

# install everything
all () {
    mn_deps
}

# base (non-OpenFlow) bits - Mininet Python bits, dependencies
mn_deps () {
    # check for OpenFlow support - 6.1 and later. Technically it works but
    # will only be able to do non-OFP networks.
    if [ $( expr ${release} '<' 6.1 ) -eq 1 ]; then
        printf '%s\n' \
            "Detected release:${release}"\
	    "Warning - OpenFlow is only supported by releases 6.1 and newer"\
	    "Retry after updating to a newer release"
	exit 1
    fi

    $install python-2.7.13p2 socat iperf help2man py-setuptools pyflakes \
        pylint pep8 py-pexpect

    printf '%s\n' "Installing Mininet core"
    cur=$(pwd -P)
    cd ${MININET_DIR}/mininet
    doas make install
    doas cp util/switchd.conf /etc/switchd.mininet.conf
    cd ${cur}
}

mn_undo () {
    printf '%s\n' "Uninstalling Mininet core"
    cur=$(pwd -P)
    cd ${MININET_DIR}/mininet
    doas make uninstall
    doas rm /etc/switchd.mininet.conf
    cd ${cur}
}

# Install RYU. `pip install ryu` should actually be sufficient.
#ryu () {
#    printf '%s\n' "Installing RYU..."
#
#    $install python py27-setuptools py27-eventlet py27-routes \
#        py27-webob py27-paramiko py27-pip py27-msgpack-python
#    pip install oslo.config tinyrpc ovs
#
#    # fetch RYU
#    cd $MININET_DIR
#    git clone git://github.com/osrg/ryu.git ryu
#    cd ryu
#
#    # install ryu
#    doas python ./setup.py install
#}

usage () {
    printf '%s\n' \
        "" \
        "Usage: $(basename $0) [-anh]" \
        "" \
        "options:" \
        " -a: (default) install (A)ll packages" \
        " -h: print this (H)elp message" \
        " -n: install Mini(N)et dependencies + core files" \
        " -u: (u)ninstall Mininet core files" \
        " -y: install R(y)u Controller"
    exit 2
}

if [ $# -eq 0 ]; then
    all
else
    while getopts 'ahnu' OPTION; do
        case $OPTION in
            a)    all ;;
            h)    usage ;;
            n)    mn_deps ;;
            u)    mn_undo ;;
            # y)    ryu ;;     #eventually, maybe
            ?)    usage ;;
        esac
    done
    shift $(($OPTIND - 1))
fi
