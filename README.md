<!-- TOC depthFrom:1 depthTo:6 withLinks:1 updateOnSave:1 orderedList:0 -->

- [Name](#name)
- [Description](#description)
- [Dependencies](#dependencies)
- [Installation](#installation)
	- [From source](#from-source)
	- [Docker](#docker)
- [Usage](#usage)
	- [Starting Worker (Slave server)](#starting-worker-slave-server)
		- [Manual execution](#manual-execution)
		- [Service execution](#service-execution)

<!-- /TOC -->
![Coverage](https://gitlab.ics.muni.cz/cryton/cryton-worker/badges/master/coverage.svg)
# Name
Cryton worker

# Description
Cryton worker is a module for executing Cryton attack modules both locally and remotely. To control Cryton worker, Cryton Core is needed (https://gitlab.ics.muni.cz/cryton/cryton-core).
Cryton worker utilizes RabbitMQ (https://www.rabbitmq.com/) as it's messaging protocol for asynchronous RPC.

# Dependencies

## For docker
* docker.io
* docker-compose

## For manual installation
* python3.8
* metasploit-framework
* (optional) pipenv

# Installation

Important note: this guide only explains how to install **Cryton Worker** package. For being able to execute the attack scenarios, you also need to install the **Cryton Core** package. If you want to use attack modules provided by Cryton, you have to also install **Cryton Modules**.

For correct installation you need to update `.env` file. For example `CRYTON_WORKER_RABBIT_SRV_ADDR` must contain the same address as you rabbit server and `CRYTON_WORKER_RABBIT_WORKER_PREFIX` must be the same as the one saved in Cryton Core.
## From source (recommended)

For manual installation all you need to do is **export variables** and **run the setup script**.

~~~~
$ python3 setup.py install
~~~~

You can also install this inside a virtual environment using pipenv.
~~~~
$ pipenv shell
(cryton-worker) $ python setup.py install
~~~~

## Docker

**NOTICE: Following guide won't describe how to install or mount applications used by modules.**

First make sure you have Docker installed:

~~~~
user@localhost:~ $ sudo apt install docker.io docker-compose
~~~~ 

Add yourself to the group docker so you can work with docker CLI without sudo:

~~~~
user@localhost:~ $ sudo groupadd docker
user@localhost:~ $ sudo usermod -aG docker $USER
user@localhost:~ $ newgrp docker 
user@localhost:~ $ docker run hello-world
~~~~

Now, run docker-compose, which will pull, build and start all necessary docker images:
~~~~
user@localhost:~ $ cd cryton-worker/
user@localhost:~ /cryton-worker $ docker-compose up -d
~~~~

This process might take a while, especially if it is the first time you run it - Cryton-Worker image must be built.
After a while you should see something like this:
~~~~
Creating cryton_worker ... done
~~~~

Everything should be set. Check if the installation was successful:

~~~~
user@localhost:~ /cryton-core $ docker-compose ps
    Name           Command      State   Ports
---------------------------------------------
cryton_worker   cryton-worker   Up 
~~~~

If is in state `Restarting`, something went wrong. Please check if Rabbit address is correct.

# Usage

For Cryton core to be able to run it's attack modules it has to command the worker service, which takes care of execution. If such worker service is run remotely (on separate machine), it is called **Slave**. The installation of such a Slave is the same as locally - all you need to do is to install the package and start the service.

If you want to execute the modules using Slaves, you have to provide **hosts file** - a file with the Slaves you have under control. This file also contains other hosts you are specifying for the Plan template.

## Starting Worker (Slave server)
There are two ways of running the listening Worker. You can either run it manually or create a service to be run by systemd.

### Manual execution

~~~~
$ cryton-worker
 [*] Waiting for messages. To exit press CTRL+C
~~~~

### Service execution
For configuring the service, you can simply copy the file from repository (*cryton_worker/etc/systemd-service/cryton-worker.service*).
*Note: change WorkingDirectory to the actual path to your Cryton Worker directory*

~~~~
[Unit]
Description=Cryton worker
After=multi-user.target
Conflicts=getty@tty1.service

[Service]
Type=simple
WorkingDirectory=/opt/cryton-worker
ExecStart=/usr/local/bin/pipenv run cryton-worker
StandardInput=tty-force

[Install]
WantedBy=multi-user.target
~~~~
