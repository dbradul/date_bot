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
	docker-compose build --force-rm

rebuild:
	docker-compose build --force-rm --no-cache

logs:
	docker-compose logs -f --tail=100

top:
	docker-compose top

restart-browser:
	docker-compose restart browser

restart-sender:
	docker-compose restart -t 0 sender


#######################################

run-tg-bot:
	docker run -it --rm --env-file .env -v /var/run/docker.sock:/var/run/docker.sock -v ${PWD}/src:/app/src  date_parser python /app/src/main.py