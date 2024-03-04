WORKDIR=$(shell pwd)
IMAGE?=licor

default:
	@echo ${WORKDIR}


build:
	docker build --pull -f Dockerfile -t ${IMAGE}:latest .


rm:
	docker rm -f ${IMAGE}


deploy:
	docker run -d --rm --name ${IMAGE} \
	       --entrypoint '/bin/sh' ${IMAGE} -c 'while true; do date; sleep 10; done'
run:
	docker run ${IMAGE}

interactive:
	docker exec -it ${IMAGE} bash