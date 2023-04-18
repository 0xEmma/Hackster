#!/bin/sh

while ! mysqladmin ping -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASSWORD --silent; do
  sleep 1
done

# Run migrations & start the bot
alembic upgrade head && poetry run task start
