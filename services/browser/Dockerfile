# Use an official and latest Ubuntu LST as a parent image
FROM ubuntu:20.04

# Fetch latest security patches
#RUN echo "deb http://security.debian.org/ buster/updates main contrib non-free" >> /etc/apt/sources.list
RUN apt-get update

ENV TZ=Europe/Kiev
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install system wise libs
RUN apt-get install -y \
    socat wget xvfb unzip vim tmux

# Install chrome browser
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN dpkg -i google-chrome-stable_current_amd64.deb; exit 0
RUN apt-get update
RUN apt install -f -y
RUN dpkg -i google-chrome-stable_current_amd64.deb
RUN google-chrome --version

# Copy the current directory contents into the container at /app
RUN mkdir /app
WORKDIR /app
COPY ./start-browser.sh ./start-browser.sh

RUN mkdir /app/data
WORKDIR /app/data

# Define environment variable
ENV NAME Browser

# Extra settings
EXPOSE 9223

# Run app
CMD ["/bin/bash"]
