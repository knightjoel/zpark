#!/bin/sh
#
# zpark_alert.sh <sendto> <subject> <message>

zpark_url=""
zpark_api_token=""


##############################################################################

ZPARK_URL=${ZPARK_URL:-$zpark_url}
ZPARK_API_TOKEN=${ZPARK_API_TOKEN:-$zpark_api_token}

if [ -z "$ZPARK_URL" ]; then
	echo "You must set the ZPARK_URL environment variable or the zpark_url variable inside this script to the top level URL where the Zpark bot is running."
	echo "Eg: https://zpark.example.domain:8000"
	exit 1
fi
if [ -z "$ZPARK_API_TOKEN" ]; then
	echo "You must set the ZPARK_API_TOKEN environment variable or the zpark_api_token variable inside this script to match the SB_API_TOKEN value configured in the Zpark app.cfg file."
	exit 1
fi

which jo >/dev/null 2>&1
if [ $? -ne 0 ]; then
	echo "This script depends on the 'jo' CLI tool (https://github.com/jpmens/jo)."
	echo "Please make sure it's installed and in your PATH."
	exit 1
fi

if [ -z "$3" ]; then
	echo "Usage: $0 <sendto> <subject> <message>"
	exit 1
fi

json=`jo to="$1" subject="$2" message="$3"`
curl \
	-H "Content-Type: application/json" \
	-H "Token: $ZPARK_API_TOKEN" \
	-X POST \
	--data-raw "$json" \
	${ZPARK_URL}/api/v1/alert

