FROM ubuntu:18.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get -y install wget vim git

WORKDIR /home/workspace
