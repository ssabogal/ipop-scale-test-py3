#!/usr/bin/env python

#sudo apt-get install python3-tk

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

CONFIG_FILE="node-config.json"

def lxc_install():
    cmd("bash ./node.bash lxc-install")
def ejabberd_install():
    cmd("bash ./node.bash ejabberd-install")
def turnserver_install():
    cmd("bash ./node.bash turnserver-install")
def network_config():
    cmd("bash ./node.bash network-config")

def lxc_deploy(start, end):
    cmd("bash ./node.bash lxc-deploy "+str(start)+" "+str(end))
def ejabberd_deploy(size):
    cmd("bash ./node.bash ejabberd-deploy "+str(size))
def turnserver_deploy(size):
    cmd("bash ./node.bash turnserver-deploy "+str(size))

def lxc_clear():
    cmd("bash ./node.bash lxc-clear")
def ejabberd_clear():
    cmd("bash ./node.bash ejabberd-clear")
def turnserver_clear():
    cmd("bash ./node.bash turnserver-clear")

def lxc_ipop_source():
    cmd("bash ./node.bash lxc-ipop-source")
def lxc_ipop_config(params):
    cmd("bash ./node.bash lxc-ipop-config "+ltos(params))
def lxc_ipop_run(lxc_list):
    cmd("bash ./node.bash lxc-ipop-run "+ltos(lxc_list))
def lxc_ipop_stop(lxc_list):
    cmd("bash ./node.bash lxc-ipop-stop "+ltos(lxc_list))

def forwarder_run(forwarder_port, forwarded_port):
    cmd("bash ./node.bash forwarder-run "+forwarder_port+" "+forwarded_port)

def main():

    ### change pwd to script location
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    ### read configuration file
    cmd("touch "+CONFIG_FILE)
    f = open(CONFIG_FILE, 'r+')
    try:
        config = json.load(f)
    except:
        config = {}
        json.dump(config, f, indent = 4)
    f.close()

    args = sys.argv[1:]

    if len(sys.argv) == 1:
        print(
            "usage:                                                             \n"\
            "  testbed configurations                                           \n"\
            "    install              : prepare testbed dependencies            \n"\
            "    init    <worker s e>                                           \n"\
            "            <server s>   : initialize testbed (using node-config)  \n"\
            "    clear                : clear testbed                           \n"\
            "    source               : update sources in the LXCs              \n"\
            "    config  <vpn_type>                                             \n"\
            "            <serv_addr>                                            \n"\
            "            <fwdr_addr>                                            \n"\
            "            <fwdr_port>                                            \n"\
            "            [options]    : update IPOP config file in the LXCs     \n"\
            "                                                                   \n"\
            "  IPOP network stimulation                                         \n"\
            "    run     <list | all> : run IPOP instance(s) in the LXC(s)      \n"\
            "    stop    <list | all> : stop IPOP instance(s) in the LXC(s)     \n"\
            "                                                                   \n"\
            "  utilities                                                        \n"\
            "    forward <fwdr_addr>                                            \n"\
            "            <fwdr_port>                                            \n"\
            "            <fwdd_port>  : forward IPOP state reports              \n"
        )
        sys.exit(1)

    ### testbed configurations
    if   (args[0] == "install"):

        lxc_install()
        ejabberd_install()
        turnserver_install()
        network_config()

    elif (args[0] == "init"):

        # parse node configuration
        config = {}
        for i in range(len(args)):
            if args[i] == "worker":
                config["worker"] = {
                    "start": int(args[i+1]),
                    "end": int(args[i+2])
                }
            if args[i] == "server":
                config["server"] = {
                    "size": int(args[i+1])
                }
            if args[i] == "forwarder":
                config["forwarder"] = {}

        # save node configuration
        f = open(CONFIG_FILE, 'r+')
        json.dump(config, f, indent = 4)
        f.close()

        if "worker" in config:
            lxc_deploy(config["worker"]["start"], config["worker"]["end"])

        if "server" in config:
            ejabberd_deploy(config["server"]["size"])
            turnserver_deploy(config["server"]["size"])

    elif (args[0] == "clear"):

        if "worker" in config:
            lxc_clear()

        if "server" in config:
            ejabberd_clear()
            turnserver_clear()

        # clear node configuration
        config = {}
        f = open(CONFIG_FILE, 'r+')
        json.dump(config, f, indent = 4)
        f.close()

    elif (args[0] == "source"):

        if "worker" in config:
            lxc_ipop_source()

    elif (args[0] == "config"):
        params = args[1:]

        if "worker" in config:
            lxc_ipop_config(params)

    ### IPOP network stimulations
    elif (args[0] == "run"):
        lxc_list = args[1:]

        if "worker" in config:

            # screen LXC list
            scr_lxc_list = []
            if "all" in lxc_list:
                scr_lxc_list = list(range(config["worker"]["start"], config["worker"]["end"]+1))
            else:
                for lxc in list(map(int, lxc_list)):
                    if config["worker"]["start"] <= lxc and lxc <= config["worker"]["end"]:
                        scr_lxc_list.append(lxc)

            lxc_ipop_run(scr_lxc_list)

    elif (args[0] == "stop"):
        lxc_list = args[1:]

        if "worker" in config:

            # screen LXC list
            scr_lxc_list = []
            if "all" in lxc_list:
                scr_lxc_list = list(range(config["worker"]["start"], config["worker"]["end"]+1))
            else:
                for lxc in list(map(int, lxc_list)):
                    if config["worker"]["start"] <= lxc and lxc <= config["worker"]["end"]:
                        scr_lxc_list.append(lxc)

            lxc_ipop_stop(scr_lxc_list)

    ### utilities
    elif (args[0] == "forward"):
        forwarder_addr = args[1]
        forwarder_port = args[2]
        forwarded_port = args[3]

        if "forwarder" in config:
            forwarder_run(forwarder_port, forwarded_port)


    else:
        print("unrecognized command")

if __name__ == "__main__":
    main()
