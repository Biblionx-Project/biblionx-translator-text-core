# Biblionx Translator Text Core
CURR_DIR	:=	$(shell pwd)
UTIL_PYCACHE	:=	"$(CURR_DIR)/src/util/__pycache__"
VENV_PYTHON	:=	$(CURR_DIR)/.venv/bin/python

CORE_CONFIG_FILE	:=	"$(CURR_DIR)/src/config/settings.ini"
LOGGER_CONFIG_FILE	:=	"$(CURR_DIR)/src/config/logging.ini"
IMAGE_NAME	:=	biblionx/biblionx-translator-text-core:latest

install:
	@bash install.sh

start:
	@CORE_CONFIG_FILE=$(CORE_CONFIG_FILE) \
	LOGGER_CONFIG_FILE=$(LOGGER_CONFIG_FILE) \
	$(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),python3) src/worker.py

dev:
	@:$(eval CORE_CONFIG_FILE := "$(CURR_DIR)/src/config/settings-dev.ini")
	@:$(eval LOGGER_CONFIG_FILE := "$(CURR_DIR)/src/config/logging-dev.ini")

stage:
	@:$(eval LOGGER_CONFIG_FILE := "$(CURR_DIR)/src/config/logging-dev.ini")

docker-build:
	docker build -t $(IMAGE_NAME) .

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	@echo -n "Cleaning... "
	@$(RM) -r $(UTIL_PYCACHE)
	@echo "\33[32;5mOK\033[m" || echo "\33[31;5mERROR\33[m"

.PHONY: install start dev stage docker-build docker-up docker-down clean
