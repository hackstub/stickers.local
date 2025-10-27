for FILE in $(find ./uploads/ -type f | sort); do echo "$FILE"; touch "$FILE"; sleep 0.1; done
