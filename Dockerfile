FROM --platform=linux/amd64 python:3.9

# install opencv & python-venv reqs
RUN apt-get update --no-install-recommends \
    && apt-get install libsm6 libxext6 libgl1-mesa-glx python3-venv --no-install-recommends -y

RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN if [[ "$(uname -m)" == "x86_64" ]] ; then apt install ./google-chrome-stable_current_amd64.deb -y; else echo Non x86_64 systems do not support chrome deb ; fi
RUN rm ./google-chrome-stable_current_amd64.deb

# set username & uid inside docker
ARG UNAME=user1
ARG UID=1000
ENV WORKDIR="/home/$UNAME/chatbot_backend"

# add user UNAME as a member of the sudoers group
RUN useradd -rm --home-dir "/home/$UNAME" --shell /bin/bash -g root -G sudo -u "$UID" "$UNAME"

# set workdir
WORKDIR ${WORKDIR}

# setup python env vars & virtual env
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONBUFFERED 1

ENV VIRTUAL_ENV="/home/$UNAME/venv"
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install python dependencies
RUN pip install pip==23.1.2
COPY requirements.txt  "$WORKDIR/requirements.txt"
RUN pip install --no-cache-dir --default-timeout=100 -r "$WORKDIR/requirements.txt"

# remove cache
RUN pip cache purge \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /root/.cache/pip

# copy all files to src & exclude those in dockerignore
COPY . "$WORKDIR"

# change file ownership to docker user
RUN chown -R "$UNAME" "$WORKDIR"

USER "$UNAME"
CMD ["python", "app/server.py", "--port", "8080"]