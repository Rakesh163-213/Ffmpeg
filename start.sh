##!/bin/bash

echo "🔥 Starting the bot..."

# Any setup you want here
# e.g., export ENV vars if not using .env

# Finally, run the bot
python main.py
echo "Starting the bot"
python main.py &
python app.py
