#!/bin/bash

# export env vars
export $(cat .env | sed 's/#.*//g' | xargs)

# restart in infinite loop
while :
do
  echo "Starting sender bot..."
#  /home/dbhost/.local/share/virtualenvs/date_parser-qy-y-OSW/bin/python src/main.py
  .venv/bin/python src/main.py
  sleep 1
done