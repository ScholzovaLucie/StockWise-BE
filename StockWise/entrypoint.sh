if [ "$WAIT_FOR_DATABASE" = 1 ]; then
  echo "Waiting for database..."

  while ! nc -z "$DB_HOST" "$DB_PORT"; do
    sleep 0.1
  done

  echo "database started"
fi

if [ "$START_CRON" = 1 ]; then
  echo "Starting Cron service..."

  printenv > /etc/environment
  cron
fi

if [ "$RUN_MIGRATIONS" = 1 ]; then
  printf "Starting to migrate database..."

  python manage.py migrate
fi


if [ "$COLLECTSTATIC" = 1 ]; then
  printf "Starting to collect static files..."

  python python manage.py collectstatic --noinput


  printf "Starting generate documentation..."
  cd sources
  sphinx-build -b html ../source ../../media/documentation/ -v

fi



exec "$@"