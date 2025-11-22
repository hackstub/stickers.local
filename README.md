# `stickers.local`

This is a Flask app to manage a collection of stickers and print them using a Brother QL thermal label printer

## Scripts

In `scripts`:
- `convert.sh` to apply transformation to an image before adding it to the collection
- `print.sh` to print an image

IMPORTANT : to be able to access the printer, the user needs to be in the `lp` group : `usermod -a -G lp <user>` (and the restart your unix session)

## Developement

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
cd scripts

(cd assets && bash fetch_assets)
```

Download the appropriate executable of [didder](https://github.com/makew0rld/didder/releases/tag/v1.3.0) in `scripts/` and edit `print.sh` accordingly (#FIXME ^^)

And then start the dev server:

```bash
source venv/bin/activate
FLASK_APP=app.py FLASK_ENV=development flask --debug run
```
To be able to connect to it via the local network, add `--host 0.0.0.0` at the end of the command.


## Lancer le service stickers.local au démarrage

[details]

Traduction de [linode.com](https://www.linode.com/docs/guides/start-service-at-boot/) :

Créer le script `stickers.sh` que le service va gérer : 
```nano stickers.sh```

Avec le contenu suivant :
```bash
cd /home/pi/stickers.local
FLASK_APP=app.py FLASK_ENV=development flask run
```

Déplacer le script dans `/usr/bin` et le rendre exécutable :

```bash
sudo mv stickers.sh /usr/bin/stickers.sh
sudo chmod +x /usr/bin/stickers.sh
```

Create a Unit file to define a systemd service in your application, where /opt/myapp/ is the path to your application directory.

Créer un fichier Unit pour définir un service systemd pour l'application contenue dans le dossier `/home/pi/stickers.local`

File: `/home/pi/stickers.local/stickers.service`

```bash
[Unit]
Description=Interface d'impression de stickers.

[Service]
Type=simple
ExecStart=/bin/bash /usr/bin/stickers.sh

[Install]
WantedBy=multi-user.target
```

Ce code définit un module qui exécutera `/usr/bin/stickers.sh` via bash.

La directive `ExecStart` spécifie la commande à exécuter.
La section `[Install]` spécifie les modalités qui lui permettront de tourner quand on veut.

Enregister le service `stickers` dans le système :

```sh
sudo systemctl enable /home/pi/stickers.local/stickers.service
```

If the `[Install]` section is present, this creates the necessary symlinks in `/etc/systemd/system/`.

Pour plus d'information sur les paramètres des modules systemd, rendez-vous sur la [documentation de systemd](https://www.freedesktop.org/wiki/Software/systemd/).

### Start and Enable the Service

Once you have a unit file, you are ready to test the service:

```sh
sudo systemctl start stickers.service
```

Check the status of the service:

```sh
sudo systemctl status stickers.service
```

If the service is running correctly, the output should resemble the following:

```sh
● stickers.service - Interface d'impression de stickers.
     Loaded: loaded (/etc/systemd/system/stickers.service; enabled; preset: enabled)
     Active: active (running) since Fri 2025-11-21 01:59:10 CET; 33s ago
   Main PID: 1539 (bash)
      Tasks: 2 (limit: 753)
        CPU: 1.213s
     CGroup: /system.slice/stickers.service
             ├─1539 /bin/bash /usr/bin/stickers.sh
             └─1541 /usr/bin/python3 /usr/bin/flask run --host 0.0.0.0

Nov 21 01:59:10 stickoeur systemd[1]: Started stickers.service - Interface d'impression de st>
Nov 21 01:59:11 stickoeur bash[1541]:  * Serving Flask app 'app.py'
Nov 21 01:59:11 stickoeur bash[1541]:  * Debug mode: off
Nov 21 01:59:11 stickoeur bash[1541]: WARNING: This is a development server. Do not use it in>
Nov 21 01:59:11 stickoeur bash[1541]:  * Running on all addresses (0.0.0.0)
Nov 21 01:59:11 stickoeur bash[1541]:  * Running on http://127.0.0.1:5000
Nov 21 01:59:11 stickoeur bash[1541]:  * Running on http://192.168.100.100:5000
Nov 21 01:59:11 stickoeur bash[1541]: Press CTRL+C to quit
```

The service can be stopped or restarted using standard systemd commands:

```sh
sudo systemctl stop stickers
sudo systemctl restart stickers
```

Finally, use the enable command to ensure that the service starts whenever the system boots:

```sh
sudo systemctl enable stickers
```
Which should output:
```
Created symlink from `/etc/systemd/system/multi-user.target.wants/stickers.service` to `/lib/systemd/system/stickers.service`.
```

Reboot your Linode from the Linode Manager and check the status of the service:

```sh
sudo systemctl status stickers
```

You should see that the service logged its start time immediately after booting:

```sh
● stickers.service - Interface d'impression de stickers.
     Loaded: loaded (/etc/systemd/system/stickers.service; enabled; preset: enabled)
     Active: active (running) since Fri 2025-11-21 01:59:10 CET; 33s ago
   Main PID: 1539 (bash)
      Tasks: 2 (limit: 753)
        CPU: 1.213s
     CGroup: /system.slice/stickers.service
             ├─1539 /bin/bash /usr/bin/stickers.sh
             └─1541 /usr/bin/python3 /usr/bin/flask run --host 0.0.0.0

Nov 21 01:59:10 stickoeur systemd[1]: Started stickers.service - Interface d'impression de st>
Nov 21 01:59:11 stickoeur bash[1541]:  * Serving Flask app 'app.py'
Nov 21 01:59:11 stickoeur bash[1541]:  * Debug mode: off
Nov 21 01:59:11 stickoeur bash[1541]: WARNING: This is a development server. Do not use it in>
Nov 21 01:59:11 stickoeur bash[1541]:  * Running on all addresses (0.0.0.0)
Nov 21 01:59:11 stickoeur bash[1541]:  * Running on http://127.0.0.1:5000
Nov 21 01:59:11 stickoeur bash[1541]:  * Running on http://192.168.100.100:5000
Nov 21 01:59:11 stickoeur bash[1541]: Press CTRL+C to quit
```

For more information about using systemctl commands, see the systemctl guide.

[/details]
