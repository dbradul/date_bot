.DEFAULT_GOAL := default

ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# ----------------------------------------------------------------------------------------------------------------------

default: rebootd logs

start:
	docker-compose up

startd:
	docker-compose up -d
	docker-compose logs -f --tail=100

stop:
	docker-compose down -t 1

reboot: stop start

rebootd: stop startd

restart:
	docker-compose restart

build:
	docker-compose build

rebuild:
	docker-compose build --no-cache

logs:
	docker-compose logs -f

top:
	docker-compose top

restart-browser:
	docker-compose restart browser

restart-sender:
	docker-compose restart -t 0 sender
