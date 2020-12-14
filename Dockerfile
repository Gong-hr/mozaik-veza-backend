FROM python:3.5

WORKDIR /usr/src/app

RUN pip install pip --upgrade
RUN pip install wheel --upgrade
RUN pip install setuptools --upgrade

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /root

RUN wget https://github.com/facebook/watchman/releases/download/v2020.08.10.00/watchman-v2020.08.10.00-linux.zip
RUN unzip watchman-v2020.08.10.00-linux.zip

WORKDIR /root/watchman-v2020.08.10.00-linux

RUN mkdir -p /usr/local/{bin,lib} /usr/local/var/run/watchman
RUN cp bin/* /usr/local/bin
RUN cp lib/* /usr/local/lib
RUN chmod 755 /usr/local/bin/watchman
RUN chmod 2777 /usr/local/var/run/watchman

WORKDIR /root

RUN rm watchman-v2020.08.10.00-linux -rf

RUN pip install --no-cache-dir pywatchman

RUN groupadd -g 1000 user
RUN useradd -m -u 1000 -g 1000 user

RUN pip install ipython
RUN pip install bpython

WORKDIR /usr/src/app

EXPOSE 8000
