# Biblionx Translator Text Core

Text translation core worker for **Biblionx**, a UNICDA thesis project (Trabajo de Grado) that translates
written Spanish (Dominican Republic) into **Dominican Sign Language (LSRD, Lengua de Señas Dominicana)**.

> **Architecture reference component.** The active Biblionx product is
> [`biblionx-lsrd-translator`](https://github.com/Biblionx-Project/biblionx-lsrd-translator). This repository
> documents the text translation core of the Biblionx reference architecture and is not a runtime dependency
> of the final product. See the [Biblionx-Project](https://github.com/Biblionx-Project) organization.

## Table of Contents

- [Architecture Role](#architecture-role)
- [Message Contract](#message-contract)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running Locally](#running-locally)
- [Configuration](#configuration)
- [Deployment with Docker](#deployment-with-docker)
- [Kubernetes (Helm)](#kubernetes-helm)
- [Development Tools](#development-tools)
- [Origins](#origins)

## Architecture Role

The text core is a stateless RabbitMQ worker. It sits behind the translation REST API
(`biblionx-translator-api`): the API publishes translation requests to a queue, the worker turns the input
text into a sign-language gloss, and replies on the queue named by the request's `reply_to` property.

| File | Purpose |
| --- | --- |
| [`src/worker.py`](src/worker.py) | Entry point. Consumes the translator queue, translates each message in its own thread and publishes the reply. |
| [`src/queuewrapper.py`](src/queuewrapper.py) | Pika-based consumer/publisher with connection retries (`tenacity`). |
| [`src/config.py`](src/config.py) | `pydantic-settings` configuration loaded from environment variables and `.env`. |
| [`src/healthcheck.py`](src/healthcheck.py) | Minimal HTTP server that answers `200 OK` to any `GET` request. |
| [`src/exceptionhandler.py`](src/exceptionhandler.py) | Logs invalid requests and unexpected errors. |

The gloss itself is produced by the external Python package `vlibras-translator` (imported as
`vlibras_translator`, version `1.3.0rc1`, installed with the `neural` extra from TestPyPI). The worker
reports the package version in every reply.

## Message Contract

**Request** (consumed from `TRANSLATOR_QUEUE`, default `translate.to_text`; the queue is declared non-durable):

- Body: JSON, e.g. `{"text": "Hola, ¿cómo estás?"}`
- Properties: `reply_to` (reply queue) and `correlation_id` (copied to the reply)

**Reply** (published to the default exchange with routing key `reply_to`):

```json
{"translation": "<gloss>", "version": "<translator package version>"}
```

On any failure the worker replies with `{"error": "Internal translator error."}`. Every message is
acknowledged after processing, whether it succeeded or not.

## Requirements

- Linux (Ubuntu 22.04 or 24.04; the Docker image is built on Ubuntu 24.04)
- Python 3.12 or 3.13
- A reachable [RabbitMQ](https://www.rabbitmq.com/) broker. The quickest way to get one locally is the
  service defined in [`docker-compose.yml`](docker-compose.yml):
  ```sh
  docker compose up -d rabbitmq   # AMQP on localhost:5673, management UI on localhost:15673
  ```
  Alternatively, install `rabbitmq-server` by following the
  [official Debian/Ubuntu guide](https://www.rabbitmq.com/docs/install-debian).

## Installation

### Option 1: installer script

[`install.sh`](install.sh) installs the system packages (`build-essential default-jre libhunspell-dev git-lfs`,
via `sudo apt`), creates a `.venv` virtual environment, installs [`requirements.txt`](requirements.txt) and the
translator package:

```sh
bash install.sh   # or: make install
```

### Option 2: manual

```sh
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install -r requirements.txt
python3 -m pip install \
    --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple \
    "vlibras-translator[neural]==1.3.0rc1"
```

`requirements.txt` pins the worker's own dependencies: `pika 1.4.1`, `tenacity 9.1.4`, `pydantic 2.13.4`,
`pydantic-settings 2.14.2` and `python-dotenv 1.2.2`. The [`Dockerfile`](Dockerfile) additionally pins the
translator's runtime stack (`torch 2.5.1` CPU, `spacy 3.8.16`, `nltk 3.9.4`, `numpy`, `subword-nmt`, etc.),
downloads the spaCy model and the NLTK WordNet corpus, and runs the translator once at build time so its
model files are fetched ahead of the first request.

## Running Locally

1. Copy the example configuration and adjust it (see [Configuration](#configuration)):
   ```sh
   cp .env.example .env
   ```
   If you use the Compose RabbitMQ service, set `AMQP_PORT=5673`.
2. Start the worker:
   ```sh
   make start              # uses .venv/bin/python if present, otherwise python3
   # or
   python3 src/worker.py
   ```

Note that `.env` is read from the current working directory, so run the worker from the repository root.
The health check listens on `HEALTHCHECK_PORT` (default `80`); binding a port below 1024 requires root, so
set e.g. `HEALTHCHECK_PORT=8080` when running as a regular user.

## Configuration

Settings are defined in [`src/config.py`](src/config.py) and read from environment variables or a `.env`
file (names are case-sensitive). Every setting can also be given with a `BIBLIONX_` prefix
(e.g. `BIBLIONX_AMQP_HOST`); the unprefixed name takes precedence when both are set.

| Variable | Default | Description |
| --- | --- | --- |
| `MODE` | `DEVELOPMENT` | One of `DEVELOPMENT`, `PRODUCTION`, `HOMOLOG`, `TESTING`. |
| `ENABLE_DL_TRANSLATION` | `True` | Use the neural (deep learning) translation mode. |
| `TRANSLATOR_QUEUE` | `translate.to_text` | Queue the worker consumes. |
| `HEALTHCHECK_PORT` | `80` | Port of the HTTP health check. |
| `AMQP_HOST` | `localhost` | RabbitMQ host, or a full `amqp://` URL. |
| `AMQP_PORT` | `5672` | RabbitMQ port. |
| `AMQP_USER` | `guest` | RabbitMQ user. |
| `AMQP_PASS` | `guest` | RabbitMQ password. |
| `AMQP_PREFETCH_COUNT` | `1` | Consumer prefetch count. |
| `AMQP_HEART_BEAT` | `60` | Connection heartbeat in seconds. |
| `AMQP_URI` | built from the values above | Optional explicit AMQP URI. |

See [`.env.example`](.env.example) for a complete template.

## Deployment with Docker

Requires Docker Engine with the Compose plugin (`docker compose version`).

[`docker-compose.yml`](docker-compose.yml) builds the worker image and starts it together with a RabbitMQ
broker on a shared network. Review its environment block before deploying:

```yml
BIBLIONX_AMQP_HOST: rabbitmq
BIBLIONX_AMQP_PORT: 5672
BIBLIONX_AMQP_USER: guest
BIBLIONX_AMQP_PASS: guest
BIBLIONX_AMQP_PREFETCH_COUNT: 1
BIBLIONX_TRANSLATOR_QUEUE: "translate.to_text"
BIBLIONX_ENABLE_DL_TRANSLATION: "true"
BIBLIONX_HEALTHCHECK_PORT: 80
```

Credentials can be overridden through the `AMQP_USER`/`AMQP_PASS` (worker) and
`RABBITMQ_DEFAULT_USER`/`RABBITMQ_DEFAULT_PASS` (broker) environment variables. Then run:

```sh
docker compose up -d      # or: make docker-up
docker compose down       # or: make docker-down
```

To build the image on its own: `make docker-build`.

## Kubernetes (Helm)

A Helm chart is available in [`deploy/helm`](deploy/helm). Review [`values.yaml`](deploy/helm/values.yaml)
before installing: the image repository, pull secrets, existing secret names and broker/cache credentials are
placeholders that must be replaced for your cluster.

## Development Tools

```sh
python3 -m pip install -r requirements-dev.txt   # flake8 7.3.0, pre-commit 4.6.0
pre-commit install
```

The hooks in [`.pre-commit-config.yaml`](.pre-commit-config.yaml) run pyupgrade, autopep8, flake8 and isort
before each commit. `make clean` removes cached bytecode.

## Origins

This project was initially forked from the open-source VLibras project. It has since evolved enough to stand
as an independent project of its own. Licensed under LGPLv3 — see [LICENSE](LICENSE).
