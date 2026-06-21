# syntax=docker/dockerfile:1.7
FROM quay.io/almalinuxorg/almalinux-bootc:latest

RUN dnf update -y \
    dnf install -y \
        curl \
        bash \
    dnf clean all

# End file by bootc label required
LABEL containers.bootc="1"