## Tabla de Contenidos

- **[Introducción](#introducción)**
  - [Requisitos del Sistema](#requisitos-del-sistema)
  - [Prerrequisitos](#prerrequisitos)
  - [Instalación](#instalación)
- **[Desarrollo](#desarrollo)**
- **[Despliegue](#despliegue)**
  - [Herramientas de Despliegue](#herramientas-de-despliegue)
  - [Desplegando](#desplegando)
- **[Colaboradores](#colaboradores)**
- **[Licencia](#licencia)**


## Introducción

Estas instrucciones le permitirán obtener una copia del proyecto en funcionamiento en su máquina local para fines de desarrollo y pruebas. Consulte la sección de despliegue para conocer cómo desplegar el proyecto en un sistema en producción.

### Requisitos del Sistema

* SO: Ubuntu 22.04 LTS (Jammy Jellyfish)

### Prerrequisitos

Antes de iniciar la instalación, es necesario instalar algunos prerrequisitos:

##### [RabbitMQ](https://www.rabbitmq.com/)

Siga el [script de inicio rápido](https://www.rabbitmq.com/install-debian.html#apt-quick-start-cloudsmith) de RabbitMQ:

```sh
#!/bin/sh

sudo apt-get install curl gnupg apt-transport-https -y

## Clave de firma principal de RabbitMQ
curl -1sLf "https://keys.openpgp.org/vks/v1/by-fingerprint/0A9AF2115F4687BD29803A206B73A36E6026DFCA" | sudo gpg --dearmor | sudo tee /usr/share/keyrings/com.rabbitmq.team.gpg > /dev/null
## Espejo comunitario de Cloudsmith: repositorio Erlang moderno
curl -1sLf https://ppa1.novemberain.com/gpg.E495BB49CC4BBE5B.key | sudo gpg --dearmor | sudo tee /usr/share/keyrings/rabbitmq.E495BB49CC4BBE5B.gpg > /dev/null
## Espejo comunitario de Cloudsmith: repositorio RabbitMQ
curl -1sLf https://ppa1.novemberain.com/gpg.9F4587F226208342.key | sudo gpg --dearmor | sudo tee /usr/share/keyrings/rabbitmq.9F4587F226208342.gpg > /dev/null

## Agregar repositorios apt mantenidos por el equipo de RabbitMQ
sudo tee /etc/apt/sources.list.d/rabbitmq.list <<EOF
## Proporciona lanzamientos modernos de Erlang/OTP
##
deb [signed-by=/usr/share/keyrings/rabbitmq.E495BB49CC4BBE5B.gpg] https://ppa1.novemberain.com/rabbitmq/rabbitmq-erlang/deb/ubuntu jammy main
deb-src [signed-by=/usr/share/keyrings/rabbitmq.E495BB49CC4BBE5B.gpg] https://ppa1.novemberain.com/rabbitmq/rabbitmq-erlang/deb/ubuntu jammy main

## Proporciona RabbitMQ
##
deb [signed-by=/usr/share/keyrings/rabbitmq.9F4587F226208342.gpg] https://ppa1.novemberain.com/rabbitmq/rabbitmq-server/deb/ubuntu jammy main
deb-src [signed-by=/usr/share/keyrings/rabbitmq.9F4587F226208342.gpg] https://ppa1.novemberain.com/rabbitmq/rabbitmq-server/deb/ubuntu jammy main
EOF

## Actualizar índices de paquetes
sudo apt-get update -y

## Instalar paquetes de Erlang
sudo apt-get install -y erlang-base \
                        erlang-asn1 erlang-crypto erlang-eldap erlang-ftp erlang-inets \
                        erlang-mnesia erlang-os-mon erlang-parsetools erlang-public-key \
                        erlang-runtime-tools erlang-snmp erlang-ssl \
                        erlang-syntax-tools erlang-tftp erlang-tools erlang-xmerl

## Instalar rabbitmq-server y sus dependencias
sudo apt-get install rabbitmq-server -y --fix-missing
```

##### Python 3.12 / 3.13

Se puede instalar usando conda.
Descargue y ejecute el [instalador de miniconda](https://docs.conda.io/en/latest/miniconda.html#linux-installers):
```sh
mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm -rf ~/miniconda3/miniconda.sh
source ~/miniconda3/bin/activate
conda init
```

Vuelva a iniciar sesión para finalizar la instalación.

Cree un nuevo entorno con Python 3.12 o 3.13:
```sh
conda create -n text-core python=3.12
```

Luego, active el entorno:
```sh
conda activate text-core
```


##### [VLibras Translator](https://gitlab.lavid.ufpb.br/vlibras2019/vlibras-library/vlibras-translator)

Instale el traductor de VLibras con soporte neuronal (versión 1.3.0rc1):
```sh
python3 -m pip install --upgrade --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple "vlibras-translator[neural]==1.3.0rc1"
```


## Desarrollo

Para ejecutar el worker localmente, los pasos son los siguientes:
- Instalar una versión moderna de Python (el servidor ha sido desarrollado y probado en Python 3.12+);
- Opcionalmente, cree y active un entorno virtual (`virtualenv` o `venv`):
  ```bash
  $ virtualenv venv && source venv/bin/activate

  # o, si no desea instalar `virtualenv`:
  $ python3 -m venv venv && source venv/bin/activate
  ```
- O deje que el instalador cree el entorno virtual del proyecto automáticamente:
  ```bash
  $ bash install.sh
  ```
- Instalar las dependencias requeridas (actualizadas a sus versiones modernas: `pika 1.4.1`, `tenacity 9.1.4`, `pydantic 2.13.4`, `pydantic-settings 2.14.2`, etc.):
  ```bash
  $ python3 -m venv .venv && source .venv/bin/activate
  $ python3 -m pip install -r requirements.txt
  ```
- Ejecutar el worker en modo depuración (debug) llamando al archivo fuente principal:
  ```bash
  $ python3 src/worker.py
  ```

Durante el desarrollo, también es útil ejecutar herramientas de estilo de código y linter antes de hacer commits y/o crear merge requests:
- Instalar las dependencias de desarrollo (`flake8 7.3.0`, `pre-commit 4.6.0`):
  ```bash
  $ python3 -m pip install -r requirements-dev.txt
  ```
- Habilitar el formateo y linter antes de realizar commits:
  ```bash
  $ pre-commit install
  ```

### Instalación

Después de instalar todos los prerrequisitos, inicie el núcleo de traducción (Translation Core) con el siguiente comando:

```sh
make dev start
```

## Despliegue

Estas instrucciones le permitirán poner en marcha una copia del proyecto en un sistema en producción.

### Herramientas de Despliegue

Para desplegar completamente este proyecto es necesario tener instalado y configurado Docker Engine y Docker Compose.

##### [Docker](https://www.docker.com/)

Descargue el script get-docker:

```sh
curl -fsSL https://get.docker.com -o get-docker.sh
```

Instale la última versión de Docker:

```sh
sudo sh get-docker.sh
```

##### [Docker Compose](https://docs.docker.com/compose/)

Las versiones modernas de Docker Engine incluyen el plugin de Compose por defecto. Puede verificar que está instalado ejecutando:

```sh
docker compose version
```

### Desplegando

Antes de desplegar el proyecto, verifique el archivo [docker-compose.yml](docker-compose.yml) y revise las siguientes variables de entorno:

```yml
AMQP_HOST: rabbitmq
AMQP_PORT: 5672
AMQP_USER: vlibras
AMQP_PASS: vlibras
AMQP_PREFETCH_COUNT: 1
TRANSLATOR_QUEUE: "translate.to_text"
ENABLE_DL_TRANSLATION: "false"
```

Finalmente, despliegue el proyecto ejecutando:

```sh
sudo docker compose up
```

## Colaboradores

* Jonathan Brilhante - <jonathan.brilhante@lavid.ufpb.br>
* Wesnydy Ribeiro - <wesnydy@lavid.ufpb.br>
* Diego Silva - <diego.silva@lavid.ufpb.br>

## Licencia

Este proyecto está bajo la Licencia LGPLv3 - consulte el archivo [LICENSE](LICENSE) para más detalles.
