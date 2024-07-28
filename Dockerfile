FROM python:3.10-slim

# Install odbc library
ENV ACCEPT_EULA=Y
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends curl gcc g++ gnupg unixodbc

RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update -y \
    && apt-get install -y --no-install-recommends msodbcsql17 mssql-tools \
    && apt-get clean -y \
    && echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bash_profile \
    && echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc

# # Install SSH agent
# RUN apt update && apt install openssh-client -y
# RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan bitbucket.org >> ~/.ssh/known_hosts

ARG service_name
WORKDIR /telegram-rag
COPY pyproject.toml .
# COPY README.md .
COPY .env .
ADD $service_name/src $HOME/telegram-rag/$service_name/src

# Install Poetry
RUN python -m pip install poetry==1.7.1
RUN poetry config virtualenvs.create false --local
RUN --mount=type=ssh poetry install

WORKDIR $service_name
ENTRYPOINT ["python", "src/main.py"]