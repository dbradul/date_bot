#FROM python:3.10
FROM ubuntu:20.04

# Fetch latest updates
RUN apt-get update

# Install docker
RUN apt-get install apt-transport-https ca-certificates curl software-properties-common -y
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
RUN add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
RUN apt-cache policy docker-ce
RUN apt-get install docker-ce -y
RUN curl -L "https://github.com/docker/compose/releases/download/1.27.4/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
RUN chmod +x /usr/local/bin/docker-compose


# Install system wise libs
RUN apt-get install -y --fix-missing \
    unzip vim curl wget
#    libnss3-tools libdbus-1-3 iputils-ping

#RUN add-apt-repository ppa:deadsnakes/ppa
#RUN apt-get update
#RUN apt-get install python3.10 -y

#RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 2

# Create required dirs
RUN mkdir -p /app/src
WORKDIR /app

# Install pythonand required packages
RUN apt-get install python3-pip -y
RUN pip3 install --upgrade pip
RUN pip3 install pipenv
#RUN apt-get install pipenv -y
COPY ./Pipfile ./Pipfile
COPY ./Pipfile.lock ./Pipfile.lock
RUN pipenv install --system --deploy --ignore-pipfile

RUN ln -s /usr/bin/python3 /usr/bin/python

# Copy app files
COPY ./src ./src
#COPY ./docker-compose.yml ./docker-compose.yml
#COPY ./date.db ./date.db

CMD ["/bin/bash"]
