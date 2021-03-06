#!/bin/sh

# Mininet install script with just the bits that are currently supported.
# It follows the logic/contents of `install.sh`.

dist=$(uname -s)
arch=$(uname -m)

if [ "${dist}" = "FreeBSD" ]; then
    install='sudo pkg install'
    remove='sudo pkg remove'
    pkginst='sudo pkg add'
    #install='sudo pkg -o ASSUME_ALWAYS_YES=true install'
    #remove='sudo pkg -o ASSUME_ALWAYS_YES=true remove'
    #pkginst='sudo pkg -o ASSUME_ALWAYS_YES=true add'
else
    printf '%s\n' "This version of Mininet and script is for FreeBSD," \
                  "but you are using ${dist}"
    exit 1
fi

# Get directory containing mininet folder
MININET_DIR=$( CDPATH= cd -- "$( dirname -- "$0" )/../.." && pwd -P )

# install everything
all () {
    mn_deps
    ovs
    ryu
}

# base (non-OpenFlow) bits - Mininet Python bits, dependencies
mn_deps () {
    # check for VIMAGE support
    if [ ! "$(sysctl kern.conftxt | grep 'VIMAGE\|DUMMYNET')" ]; then
        printf '%s\n' \
            "*** VIMAGE and DUMMYNET are required but seem to be missing!"\
            "Please retry after rebuilding the kernel with these options."\
            "Take a look at util/VIMAGEMOD for a sample kernel config."
        exit 1
    fi

    $install python socat psmisc xterm openssh-portable iperf help2man bash\
        py27-setuptools py27-pyflakes pylint-py27 py27-pep8 py27-pexpect #\
        # gcc gmake

    printf '%s\n' "Installing Mininet core"
    cur=$(pwd -P)
    cd ${MININET_DIR}/mininet
    sudo make install
    cd ${cur}
}

mn_undo () {
    printf '%s\n' "Uninstalling Mininet core"
    cur=$(pwd -P)
    cd ${MININET_DIR}/mininet
    sudo make uninstall
    cd ${cur}
}

# Install/uninstall OVS.
ovs () {
    if [ "$1" = '-u' ]; then
        $remove openvswitch
        return
    else
        $install openvswitch && \
        printf '%s\n' "You may wish to add the following to rc.conf:" \
                      '    ovsdb_server_enable="YES"' \
                      '    ovs_vswitchd_enable="YES"'
        # start OVSDB and vswitchd
        printf '%s\n' "starting openvswitch bits"
        service ovsdb-server onestart
        service ovs-vswitchd onestart
    fi
}

# Install RYU. `pip install ryu` should actually be sufficient.
ryu () {
    printf '%s\n' "Installing RYU..."

    $install python py27-setuptools py27-routes \
        py27-webob py27-paramiko py27-pip py27-msgpack-python
    pip install oslo.config tinyrpc ovs eventlet==0.19.0

    # fetch RYU
    cd $MININET_DIR
    git clone git://github.com/osrg/ryu.git ryu
    cd ryu

    # install ryu
    sudo python ./setup.py install
}

# Install just the non-ported dependencies. Assumed chroot
img_build () {
    cur=$(pwd)
    cd mininet
    make install
    cd $cur
    # install ryu
    /usr/local/bin/git clone git://github.com/osrg/ryu.git ryu
    cd ryu
    /usr/local/bin/python ./setup.py install
}

usage () {
    printf '%s\n' \
        "" \
        "Usage: $(basename $0) [-anh]" \
        "" \
        "options:" \
        " -a: (default) install (A)ll packages" \
        " -h: print this (H)elp message" \
        " -i: build non-port dependencies only" \
        " -n: install Mini(N)et dependencies + core files" \
        " -r: remove existing Open vSwitch packages" \
        " -u: (u)ninstall Mininet core files" \
        " -v: install Open (V)switch" \
        " -y: install R(y)u Controller"
    exit 2
}

if [ $# -eq 0 ]; then
    all
else
    while getopts 'ahinruvy' OPTION; do
        case $OPTION in
            a)    all ;;
            h)    usage ;;
            i)    img_build ;;
            n)    mn_deps ;;
            r)    ovs -u ;;
            u)    mn_undo ;;
            v)    ovs ;;
            y)    ryu ;;
            ?)    usage ;;
        esac
    done
    shift $(($OPTIND - 1))
fi
