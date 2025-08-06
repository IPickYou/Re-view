#!/bin/bash
set -e

source /opt/conda/etc/profile.d/conda.sh
conda activate review-app

echo "Starting backend..."
python api.py > backend.log 2>&1 &

cd frontend

if [ ! -d "node_modules" ]; then
  echo "Installing npm packages..."
  npm install
fi

echo "Starting frontend..."
exec npm start