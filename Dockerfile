FROM ghcr.io/hackthebox/hackster:base as builder-base
# `production` image used for runtime
FROM builder-base as production

RUN apt-get update && \
    apt-get install -y mariadb-client libmariadb-dev && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH

COPY alembic /hackster/alembic
COPY alembic.ini /hackster/alembic.ini
COPY src /hackster/src
COPY resources /hackster/resources
COPY startup.sh /hackster/startup.sh
RUN chmod +x /hackster/startup.sh

WORKDIR /hackster
ENV PYTHONPATH=/hackster
ENV HACKSTER_ENV=prod

EXPOSE 1337
# Run the start script, it will check for an /app/prestart.sh script (e.g. for migrations)
# And then will start Uvicorn
ENTRYPOINT ["/hackster/startup.sh"]
