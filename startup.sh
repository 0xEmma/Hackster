#!/bin/sh

while ! mysqladmin ping -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" --silent; do
  echo 'Database not ready yet'
  sleep 1
done

# Run migrations & start the bot
alembic upgrade head && poetry run task start
