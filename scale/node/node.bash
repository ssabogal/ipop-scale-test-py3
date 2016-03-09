#!/bin/bash

cd $(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

NET_DEV=$(ifconfig | grep eth | awk '{print $1}' | head -n 1)
HOST_IPv4=$(ifconfig $NET_DEV | grep "inet addr" | awk -F: '{print $2}' | awk '{print $1}')

# configuration file paths
NODE_EJABBERD_CONFIG="./config/ejabberd.yml"
EJABBERD_CONFIG="/etc/ejabberd/ejabberd.yml"

NODE_TURNSERVER_CONFIG="./config/turnserver.conf"
TURNSERVER_CONFIG="/etc/turnserver/turnserver.conf"
TURNSERVER_USERS="/etc/turnserver/turnusers.txt"

DEFAULT_LXC_CONFIG="/var/lib/lxc/default/config"

FORWARDER_PROGRAM="./cv_forwarder.py"
IPOP_PATH="./ipop"
LXC_IPOP_SCRIPT="/home/ubuntu/ipop/ipop.py"

case $1 in

    ("lxc-install")
        ### install LXC
        # install LXC package
        sudo apt-get update
        sudo apt-get -y install lxc

        # create default container
        sudo lxc-create -n default -t ubuntu

        # install additional packages (python and psmisc); allow tap device
        sudo chroot /var/lib/lxc/default/rootfs apt-get update
        sudo chroot /var/lib/lxc/default/rootfs apt-get install -y python psmisc iperf
        echo 'lxc.cgroup.devices.allow = c 10:200 rwm' | sudo tee --append $DEFAULT_LXC_CONFIG

        echo "a" > test.txt #XXX
        ;;

    ("ejabberd-install")
        ### install ejabberd
        # install ejabberd package
        sudo apt-get update
        sudo apt-get -y install ejabberd

        # prepare ejabberd server config file
        sudo cp $NODE_EJABBERD_CONFIG $EJABBERD_CONFIG

        # restart ejabberd service
        sudo systemctl restart ejabberd.service
        sudo ejabberdctl restart

        # wait for ejabberd service to start
        sleep 15

        # create admin user
        sudo ejabberdctl register admin ejabberd password

        echo "b" > test.txt #XXX
        ;;

    ("turnserver-install")
        ### install turnserver
        # install libconfuse0 and turnserver packages
        sudo apt-get update
        sudo apt-get -y install libconfuse0 turnserver

        # use IP aliasing to bind turnserver to this ipv4 address
        sudo ifconfig $NET_DEV:0 $HOST_IPv4 up

        # prepare turnserver config file
        sudo sed -i "s/listen_address = .*/listen_address = { \"$HOST_IPv4\" }/g" $NODE_TURNSERVER_CONFIG
        sudo cp $NODE_TURNSERVER_CONFIG $TURNSERVER_CONFIG

        echo "c" > test.txt #XXX
        ;;

    ("network-config")
        ### configure network
        # add full-cone NAT (SNAT)
        sudo iptables -t nat -A POSTROUTING -o $NET_DEV -j SNAT --to-source $HOST_IPv4

        # open TCP ports (for XMPP)
        for i in 5222 5269 5280; do
            sudo iptables -A INPUT -p tcp --dport $i -j ACCEPT
            sudo iptables -A OUTPUT -p tcp --dport $i -j ACCEPT
        done

        # open UDP ports (for STUN and TURN)
        for i in 3478 19302; do
            sudo iptables -A INPUT -p udp --sport $i -j ACCEPT
            sudo iptables -A OUTPUT -p udp --sport $i -j ACCEPT
        done

        echo "d" > test.txt #XXX
        ;;

    ("lxc-deploy")
        start=$2
        end=$3

        # clone and start N containers from default container; create tap device
        for i in $(seq $start $end); do
            sudo bash -c "
                lxc-clone default node$i;
                sudo lxc-start -n node$i --daemon;
                sudo lxc-attach -n node$i -- bash -c 'sudo mkdir /dev/net; sudo mknod /dev/net/tun c 10 200; sudo chmod 0666 /dev/net/tun';
            " &
        done
        wait
        ;;

    ("ejabberd-deploy")
        size=$2

        ### initialize XMPP/STUN services
        # register IPOP users (username: node#@ejabberd, password: password)
        for i in $(seq 0 $(($size - 1))); do
            sudo ejabberdctl register "node$i" ejabberd password
        done

        # define user links
        sudo ejabberdctl srg_create ipop_vpn ejabberd ipop_vpn ipop_vpn ipop_vpn
        sudo ejabberdctl srg_user_add @all@ ejabberd ipop_vpn ejabberd
        ;;

    ("turnserver-deploy")
        size=$2

        ### initialize TURN service
        # add users to turnserver userlist
        for i in $(seq 0 $(($size - 1))); do
            echo "node$i:password:socialvpn.org:authorized" | sudo tee --append $TURNSERVER_USERS
        done

        # run turnserver
        turnserver -c $TURNSERVER_CONFIG
        ;;

    ("lxc-clear")
        # stop and delete N containers
        for lxc in $(sudo lxc-ls | grep node); do
            sudo lxc-stop -n "$lxc"; sudo lxc-destroy -n "$lxc" &
        done
        wait
        ;;

    ("ejabberd-clear")
        ### clear XMPP/STUN services
        # undefine user links
        sudo ejabberdctl srg_delete ipop_vpn ejabberd

        # unregister IPOP users
        for user in $(sudo ejabberdctl registered_users ejabberd | grep node); do
            sudo ejabberdctl unregister "$user" ejabberd
        done
        ;;

    ("turnserver-clear")
        ### clear TURN service
        # kill turnserver
        ps aux | grep -v grep | grep turnserver | awk '{print $2}' | xargs sudo kill -9

        # remove users from turnserver userlist
        echo "" | sudo tee $TURNSERVER_USERS
        ;;

    ("lxc-ipop-source")
        # update sources of each vnode
        for lxc in $(sudo lxc-ls | grep node); do
            sudo cp -r $IPOP_PATH "/var/lib/lxc/$lxc/rootfs/home/ubuntu/" &
        done
        wait
        ;;

    ("lxc-ipop-config")
        # i = X in "nodeX")
        # ${@:2:$#} = args[2:]
        params=${@:2:$#}

        for lxc in $(sudo lxc-ls | grep node); do
            i=$(echo $lxc | cut -d "e" -f2-)
            sudo lxc-attach -n "$lxc" -- bash -c "python3 $LXC_IPOP_SCRIPT config $i $params" &
        done
        wait
        ;;

    ("lxc-ipop-run")
        lxc_list=${@:2:$#}

        for i in ${lxc_list[@]}; do
            sudo lxc-attach -n "node$i" -- bash -c "python3 $LXC_IPOP_SCRIPT run"
        done
        ;;

    ("lxc-ipop-stop")
        lxc_list=${@:2:$#}

        for i in ${lxc_list[@]}; do
            sudo lxc-attach -n "node$i" -- bash -c "python3 $LXC_IPOP_SCRIPT stop"
        done
        ;;

    ("forwarder-run")
        forwarder_ipv4=$HOST_IPv4
        forwarder_port=$2
        forwarded_port=$3

        ps aux | grep -v grep | grep $FORWARDER_PROGRAM | awk '{print $2}' | xargs sudo kill -9
        nohup python3 $FORWARDER_PROGRAM $forwarder_ipv4 $forwarder_port $forwarded_port > /dev/null 2>&1 &
        ;;

esac

exit 0

