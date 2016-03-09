#!/usr/bin/env python

# TODO:     replace: bash --> python:
#               use python3-lxc to manage LXCs
#               use python3-paramiko to mange SSH/SFTP
#               use python3-nbxmpp/python3-sleekxmpp to handle ejabberd
#               use python3 to launch python programs
#               remaining things in bash:
#                   shell commands
#                   turnserver
#                   configure networking
# FIXME:    command=install: completes but does not return; <CTRL-C to continue>
# TODO:     rewrite dynamic/generalized visualizer for GVPN/SVPN
# FIXME:    thread-leak when closing multi-threaded visualizer:
#               listener continues after drawer exits

import os
import sys
import json
import shlex
import subprocess

def cmd(command):
    proc = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    ret = proc.stdout.read()[:-1].decode("utf-8")
    return ret

def ltos(l):
    s = ""
    for e in l:
        s = (s + str(e) + " ")
    return s

CONFIG_FILE="scale-config.json"
NODE_SOURCE="./node/"

def main():

    ### change pwd to script location
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    ### read configuration file
    try:
        f = open(CONFIG_FILE, 'r')
        config = json.load(f)
        f.close()
    except:
        print("scale: configuration file not found")
        sys.exit(1)

    nodes = list(set(config["workers"] + [config["server"]] + [config["forwarder"]]))

    args = sys.argv[1:]

    if len(sys.argv) == 1:
        print(
            "usage:                                                             \n"\
            "  testbed configurations                                           \n"\
            "    download               : download IPOP sources                 \n"\
            "    accept                 : add node to SSH list of known hosts   \n"\
            "    install                : prepare testbed dependencies          \n"\
            "    init                   : initialize testbed (using node-config)\n"\
            "    clear                  : clear testbed                         \n"\
            "    source                 : update sources in the nodes and LXCs  \n"\
            "    config    [options]    : update IPOP config file in the LXCs   \n"\
            "                                                                   \n"\
            "  IPOP network stimulation                                         \n"\
            "    run       <list | all> : run IPOP instance(s) in the LXC(s)    \n"\
            "    stop      <list | all> : stop IPOP instance(s) in the LXC(s)   \n"\
            "                                                                   \n"\
            "  utilities                                                        \n"\
            "    forward   <fwdd_port>  : forward IPOP state reports            \n"\
            "    visualize <fwdd_port>  : run visualizer                        \n"
        )
        sys.exit(1)

    ### testbed configurations
    if   (args[0] == "download"):
        pass

    elif (args[0] == "accept"):
        for node in nodes:
            cmd("ssh "+node+" bash -c \"echo 'added $(whoami)@$(hostname)'\"")

    elif (args[0] == "install"):

        # compress node sources
        cmd("tar -zcvf node.tar.gz "+NODE_SOURCE)

        # send node sources; instruct nodes to install
        for node in nodes:
            cmd("bash -c \"echo 'put ./node.tar.gz' | sftp "+node+"\"")
            cmd("ssh "+node+" 'tar xf ./node.tar.gz'")
            cmd("ssh "+node+" 'python3 ./node/node.py install'")

    elif (args[0] == "init"):

        i = 0
        for node in nodes:
            params = []
            if node in config["workers"]:
                start = i*config["size"]//len(config["workers"])
                end = (i+1)*config["size"]//len(config["workers"])-1
                i = i + 1

                params = params + ["worker", start, end]

            if node == config["server"]:
                params = params + ["server", config["size"]]

            if node == config["forwarder"]:
                params = params + ["forwarder"]

            # instruct node to initialize
            cmd("ssh "+node+" 'python3 node/node.py init "+ltos(params)+"'")

    elif (args[0] == "clear"):

        # instruct nodes to clear
        for node in nodes:
            cmd("ssh "+node+" 'python3 node/node.py clear'")

    elif (args[0] == "source"):

        # compress node sources
        cmd("tar -zcvf node.tar.gz "+NODE_SOURCE)

        # send node sources; instruct nodes to source
        for node in nodes:
            cmd("bash -c \"echo 'put ./node.tar.gz' | sftp "+node+"\"")
            cmd("ssh "+node+" 'tar xf ./node.tar.gz'")
            cmd("ssh "+node+" 'python3 node/node.py source'")

    elif (args[0] == "config"):

        vpn_type = args[1]
        serv_addr = config["server"].split('@')[1]
        fwdr_addr = config["forwarder"].split('@')[1]
        fwdr_port = 50101
        options = args[2:]

        params = [vpn_type, serv_addr, fwdr_addr, fwdr_port] + options

        # instruct workers to configure
        for worker in config["workers"]:
            cmd("ssh "+worker+" 'python3 node/node.py config "+ltos(params)+"'")

    ### IPOP network stimulations
    elif (args[0] == "run"):
        lxc_list = args[1:]

        # instruct workers to run IPOP instances
        for worker in config["workers"]:
            cmd("ssh "+worker+" 'python3 node/node.py run "+ltos(lxc_list)+"'")

    elif (args[0] == "stop"):
        lxc_list = args[1:]

        # instruct workers to run IPOP instances
        for worker in config["workers"]:
            cmd("ssh "+worker+" 'python3 node/node.py stop "+ltos(lxc_list)+"'")

    ### utilities
    elif (args[0] == "forward"):
        forwarder_addr = config["forwarder"].split('@')[1]
        forwarder_port = str(50101)
        forwarded_port = str(args[1])

        # instruct forwarder to forward
        cmd("ssh "+config["forwarder"]+" 'python3 node/node.py forward "+forwarder_addr+" "+forwarder_port+" "+forwarded_port+"'")

    elif (args[0] == "visualize"):
        forwarder_addr = config["forwarder"].split('@')[1]
        forwarded_port = str(args[1])
        ret = cmd("bash -c \"nohup python3 ./visualizer.py tcp "+forwarder_addr+" "+forwarded_port+" 172.31.0.0 "+str(config["size"])+" 350 > /dev/null 2>&1 &\"")
        print(ret)


    else:
        print("unrecognized command")

    f.close()

if __name__ == "__main__":
    main()
