WORKDIR := $(shell pwd)
DIRNAME := $(shell basename $(WORKDIR))

# Config
CONTAINER_NAME := $(DIRNAME)
IMAGE_NAME := $(DIRNAME)
#BUILD_TARGET := --target scanservjs-brscan4
BUILD_TARGET := 
LOCAL ?= 1

SUBMODULES := $(shell git config --file .gitmodules --get-regexp path | awk '{ print $$2 }')
#SUBMODULES := foo/ bar/ baz/

# Define variables
DATE := $(shell date +"%y%m%d")
TAG := $(shell git rev-parse --short HEAD || echo latest)
BRANCH := $(shell git rev-parse --abbrev-ref HEAD || echo latest)
BUILD_ARG := $(shell if [ -d .git ]; then echo "--build-arg GIT_COMMIT=$$(git rev-parse HEAD)"; fi)
DOCKERFILE := Dockerfile
ifeq ($(LOCAL),1)
	DOCKER_HUB_USERNAME := registry1.arakis.uk
else
	DOCKER_HUB_USERNAME := spacezorro
endif


# Default target
all: build

cron: pull build push-all

# Build the Docker image
build:
	@sudo docker build $(BUILD_ARG) $(BUILD_TARGET) -t $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(TAG) -f $(DOCKERFILE) . || { echo "Build failed"; exit 1; }
	@sudo docker tag $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(TAG) $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(BRANCH)
	@sudo docker tag $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(TAG) $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(DATE)

# Discard all local changes
discard-changes:
	@if [ -d .git ]; then \
		echo "Discarding Changes $$(pwd)..."; \
	        git reset --hard HEAD; \
	        git clean -fd; \
	else \
		echo "Not a git repository."; \
	fi

# Pull the latest changes from the current branch
pull:
	@if [ -d .git ]; then \
		echo "Pulling updates in $$(pwd)..."; \
	        git fetch origin; \
	        git pull origin $(BRANCH); \
	        git submodule foreach 'echo "Updating submodule $$name..."; git pull origin $$(git rev-parse --abbrev-ref HEAD)'; \
	else \
		echo "Not a git repository."; \
	fi
	@if [ -z "$(SUBMODULES)" ]; then \
		echo "No submodules to update."; \
	else \
		for d in $(SUBMODULES); do \
			echo "Updating $$d..."; \
			( cd $$d && git pull ); \
		done; \
	fi

# Combined update and build process
update-build: discard-changes pull build

# Run the Docker container
run:
	@sudo docker run --rm -it --name $(CONTAINER_NAME) \
		-e REGISTRY_URL=https://registry.arakis.uk -e DRY_RUN=true \
		$(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(TAG)

# Stop the container
stop:
	@sudo docker stop $(CONTAINER_NAME) || true

# Remove the container
clean: stop
	@sudo docker rm $(CONTAINER_NAME) || true

# Remove the image
clean-image: clean
	@sudo docker rmi $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(TAG) || true

# Tag and push the image to Docker Hub
push-latest: tag-latest 
	@sudo docker push $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):latest

tag-latest:
	@sudo docker tag $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(TAG) $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):latest

push-all: push-latest push

# Push the image to Docker Hub
push:
	@sudo docker push $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(TAG)
	@sudo docker push $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(BRANCH)
	@sudo docker push $(DOCKER_HUB_USERNAME)/$(IMAGE_NAME):$(DATE)

# Scrub unused build cache
scrub:
	@sudo docker buildx prune -fa

# View logs from the container
logs:
	@sudo docker logs $(CONTAINER_NAME)

# Help target
help:
	@echo "Makefile commands:"
	@echo "  make all               Build the Docker image (default target)."
	@echo "  make build             Build the Docker image using the current branch and commit hash."
	@echo "  make update-build      Discard changes, pull latest updates, and build the Docker image."
	@echo "  make run               Run the Docker container with specified network and environment settings."
	@echo "  make stop              Stop the running Docker container."
	@echo "  make clean             Remove the stopped Docker container."
	@echo "  make clean-image       Remove the Docker image corresponding to the current tag."
	@echo "  make push              Push the Docker image to Docker Hub with tags for date, branch, and commit."
	@echo "  make push-latest       Tag the image as latest and push it to Docker Hub."
	@echo "  make push-all          Push everywhere"
	@echo "  make scrub             Remove unused build cache."
	@echo "  make logs              View the logs from the running Docker container."
	@echo "  make help              Display this help message."

.PHONY: all cron build discard-changes pull update-build run stop clean clean-image push push-latest scrub logs help stackup stackdn stackdev stackrdev

