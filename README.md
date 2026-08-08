# VLibras Translator Text Core

> **Note — Biblionx-Project:** this repository is an adaptation of [VLibras](https://www.vlibras.gov.br/) kept as an architecture reference for the Biblionx thesis project (Dominican Sign Language, LSRD, text translator). The project's active, functional component is [`modelo-traductor-lsrd`](https://github.com/Biblionx-Project/modelo-traductor-lsrd); this repo is kept as a historical reference of the original VLibras ecosystem, not as an active dependency of the final product. See the [Biblionx-Project](https://github.com/Biblionx-Project) organization.

## Table of Contents

- **[Introduction](#introduction)**
  - [System Requirements](#system-requirements)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- **[Development](#development)**
- **[Deployment](#deployment)**
  - [Deployment Tools](#deployment-tools)
  - [Deploying](#deploying)
- **[Contributors](#contributors)**
- **[License](#license)**


## Introduction

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See the deployment section for notes on how to deploy the project to a production system.

### System Requirements

* OS: Ubuntu 22.04 LTS (Jammy Jellyfish)

### Prerequisites

Before starting the installation, a few prerequisites need to be installed:

##### [RabbitMQ](https://www.rabbitmq.com/)

Follow RabbitMQ's [quick start script](https://www.rabbitmq.com/install-debian.html#apt-quick-start-cloudsmith):

```sh
#!/bin/sh

sudo apt-get install curl gnupg apt-transport-https -y

## RabbitMQ main signing key
curl -1sLf "https://keys.openpgp.org/vks/v1/by-fingerprint/0A9AF2115F4687BD29803A206B73A36E6026DFCA" | sudo gpg --dearmor | sudo tee /usr/share/keyrings/com.rabbitmq.team.gpg > /dev/null
## Cloudsmith community mirror: modern Erlang repository
curl -1sLf https://ppa1.novemberain.com/gpg.E495BB49CC4BBE5B.key | sudo gpg --dearmor | sudo tee /usr/share/keyrings/rabbitmq.E495BB49CC4BBE5B.gpg > /dev/null
## Cloudsmith community mirror: RabbitMQ repository
curl -1sLf https://ppa1.novemberain.com/gpg.9F4587F226208342.key | sudo gpg --dearmor | sudo tee /usr/share/keyrings/rabbitmq.9F4587F226208342.gpg > /dev/null

## Add apt repositories maintained by the RabbitMQ team
sudo tee /etc/apt/sources.list.d/rabbitmq.list <<EOF
## Provides modern Erlang/OTP releases
##
deb [signed-by=/usr/share/keyrings/rabbitmq.E495BB49CC4BBE5B.gpg] https://ppa1.novemberain.com/rabbitmq/rabbitmq-erlang/deb/ubuntu jammy main
deb-src [signed-by=/usr/share/keyrings/rabbitmq.E495BB49CC4BBE5B.gpg] https://ppa1.novemberain.com/rabbitmq/rabbitmq-erlang/deb/ubuntu jammy main

## Provides RabbitMQ
##
deb [signed-by=/usr/share/keyrings/rabbitmq.9F4587F226208342.gpg] https://ppa1.novemberain.com/rabbitmq/rabbitmq-server/deb/ubuntu jammy main
deb-src [signed-by=/usr/share/keyrings/rabbitmq.9F4587F226208342.gpg] https://ppa1.novemberain.com/rabbitmq/rabbitmq-server/deb/ubuntu jammy main
EOF

## Update package indexes
sudo apt-get update -y

## Install Erlang packages
sudo apt-get install -y erlang-base \
                        erlang-asn1 erlang-crypto erlang-eldap erlang-ftp erlang-inets \
                        erlang-mnesia erlang-os-mon erlang-parsetools erlang-public-key \
                        erlang-runtime-tools erlang-snmp erlang-ssl \
                        erlang-syntax-tools erlang-tftp erlang-tools erlang-xmerl

## Install rabbitmq-server and its dependencies
sudo apt-get install rabbitmq-server -y --fix-missing
```

##### Python 3.12 / 3.13

Can be installed using conda.
Download and run the [miniconda installer](https://docs.conda.io/en/latest/miniconda.html#linux-installers):
```sh
mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm -rf ~/miniconda3/miniconda.sh
source ~/miniconda3/bin/activate
conda init
```

Log back in to finish the installation.

Create a new environment with Python 3.12 or 3.13:
```sh
conda create -n text-core python=3.12
```

Then activate the environment:
```sh
conda activate text-core
```


##### [VLibras Translator](https://gitlab.lavid.ufpb.br/vlibras2019/vlibras-library/vlibras-translator)

Install the VLibras translator with neural support (version 1.3.0rc1):
```sh
python3 -m pip install --upgrade --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple "vlibras-translator[neural]==1.3.0rc1"
```


## Development

To run the worker locally, follow these steps:
- Install a modern version of Python (the server was developed and tested on Python 3.12+);
- Optionally, create and activate a virtual environment (`virtualenv` or `venv`):
  ```bash
  $ virtualenv venv && source venv/bin/activate

  # or, if you don't want to install `virtualenv`:
  $ python3 -m venv venv && source venv/bin/activate
  ```
- Or let the installer create the project's virtual environment automatically:
  ```bash
  $ bash install.sh
  ```
- Install the required dependencies (updated to their modern versions: `pika 1.4.1`, `tenacity 9.1.4`, `pydantic 2.13.4`, `pydantic-settings 2.14.2`, etc.):
  ```bash
  $ python3 -m venv .venv && source .venv/bin/activate
  $ python3 -m pip install -r requirements.txt
  ```
- Run the worker in debug mode by calling the main source file:
  ```bash
  $ python3 src/worker.py
  ```

During development, it's also useful to run code style and linter tools before committing and/or opening merge requests:
- Install the development dependencies (`flake8 7.3.0`, `pre-commit 4.6.0`):
  ```bash
  $ python3 -m pip install -r requirements-dev.txt
  ```
- Enable formatting and linting before commits:
  ```bash
  $ pre-commit install
  ```

### Installation

After installing all the prerequisites, start the Translation Core with the following command:

```sh
make dev start
```

## Deployment

These instructions will get a copy of the project running on a production system.

### Deployment Tools

To fully deploy this project you need Docker Engine and Docker Compose installed and configured.

##### [Docker](https://www.docker.com/)

Download the get-docker script:

```sh
curl -fsSL https://get.docker.com -o get-docker.sh
```

Install the latest version of Docker:

```sh
sudo sh get-docker.sh
```

##### [Docker Compose](https://docs.docker.com/compose/)

Modern versions of Docker Engine include the Compose plugin by default. You can verify it's installed by running:

```sh
docker compose version
```

### Deploying

Before deploying the project, check the [docker-compose.yml](docker-compose.yml) file and review the following environment variables:

```yml
AMQP_HOST: rabbitmq
AMQP_PORT: 5672
AMQP_USER: vlibras
AMQP_PASS: vlibras
AMQP_PREFETCH_COUNT: 1
TRANSLATOR_QUEUE: "translate.to_text"
ENABLE_DL_TRANSLATION: "false"
```

Finally, deploy the project by running:

```sh
sudo docker compose up
```

## Contributors

* Jonathan Brilhante - <jonathan.brilhante@lavid.ufpb.br>
* Wesnydy Ribeiro - <wesnydy@lavid.ufpb.br>
* Diego Silva - <diego.silva@lavid.ufpb.br>

## License

This project is licensed under LGPLv3 - see the [LICENSE](LICENSE) file for details.
