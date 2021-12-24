FROM python:3.9

# Fetch latest updates
RUN apt-get update

# Install chromedriver
WORKDIR /tmp
RUN CHROME_DRIVER_VERSION=$(curl https://chromedriver.storage.googleapis.com/LATEST_RELEASE) \
    && echo $CHROME_DRIVER_VERSION \
    && wget https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip \
    && unzip -o chromedriver_linux64.zip -d /usr/bin/ \
    && mkdir -p /usr/lib/chromium-browser \
    && cp /usr/bin/chromedriver /usr/lib/chromium-browser/chromedriver

# Install system wise libs
RUN apt-get install -y --fix-missing \
    unzip vim curl wget \
    libnss3-tools libdbus-1-3 iputils-ping

# make required dirs
RUN mkdir -p /app/src
WORKDIR /app

# Install pythonand required packages
RUN pip3 install --upgrade pip
RUN pip3 install pipenv
COPY ./Pipfile ./Pipfile
COPY ./Pipfile.lock ./Pipfile.lock
RUN pipenv install --system --deploy --ignore-pipfile

# Copy app files
COPY ./src ./src
COPY ./date.db ./date.db

CMD ["/bin/bash"]
