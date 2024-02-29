WORKDIR=$(shell pwd)
IMAGE?=plugin-usb

default:
	@echo ${WORKDIR}


build:
	docker build --pull -f Dockerfile -t ${IMAGE}:latest .


rm:
	docker rm -f ${IMAGE}


deploy:
	docker run -d --rm --name ${IMAGE} \
	       --device=/dev/ttyUSB0 \
	       --entrypoint '/bin/sh' ${IMAGE} -c 'while true; do date; sleep 10; done'
run:
	docker run --device=/dev/ttyUSB0 ${IMAGE}

interactive:
	docker exec -it ${IMAGE} bash