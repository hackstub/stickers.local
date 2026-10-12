for FILE in $(find ./uploads/ -type f | sort | tac); do echo "$FILE"; touch "$FILE"; sleep 0.1; done
