# `stickers.local`

<p align="center"><img src="assets/logo.png" width="500px" /></p>

This is a web app to manage a collection of stickers and print them using a Brother QL thermal label printer

- It relies on [the `brother_ql` python lib](https://github.com/pklaus/brother_ql)
- The web front is built using [Flask](https://flask.palletsprojects.com/en/stable/), [Tailwind CSS](https://tailwindcss.com/) and [HTMX](https://four.htmx.org/)
- Processing the image before printing is done with [Pillow](https://pypi.org/project/pillow/) (color/contrast manipulation, label generation), [Imagemagick](https://imagemagick.org/) (resize) and [Didder](https://github.com/makew0rld/didder) (dithering)
- Optional printing queue uses [redis](https://redis.io/) and [RQ](https://python-rq.org/)/[Flask-RQ](https://flask-rq.readthedocs.io/)

## Setup

```bash
apt install fontconfig
apt install redis-server # If you want to enable the print queue

python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt

(cd assets && bash fetch_assets)
```

Download the appropriate executable of [didder](https://github.com/makew0rld/didder/releases/tag/v1.3.0) in `assets/`

**IMPORTANT** : to be able to access the printer, your user needs to be in the `lp` group : `usermod -a -G lp $USER`. This requires to restart your unix session for this to be fully propagated. The simplest way is typically to reboot the entire computer.

## Configuration

Default configuration values should be fine, but if you need to, you can copy and tweak the configuration with:

```
cp env.example .env
nano .env
```

You can also put fonts (for text label generation) in `assets/fonts/`. For example you can find and download fonts at https://fontmeme.com/fonts/. You need to extract the `.otf` or `.ttf` into `assets/fonts/`.

## Development

Start the dev server:

```bash
source venv/bin/activate
flask run --debug
```

## Production deployment

The naive approach is to just run `flask run --host 0.0.0.0` to expose it on the local network. But this requires to keep a terminal open running this command and only runs a single worker (and Flask devs do not recommend the dev server to be used for production).

A more long-term solution is to configure a systemd service that starts at boot. Under the hood, it uses Gunicorn which allows for multiple worker, dumps the logs in logfiles, etc

### `systemd` setup

This assume that you did setup stuff in `/var/www/stickers`

```bash
# Create the needed user and chown all the files
useradd stickers
usermod -a -G lp stickers
chown -R stickers:stickers /var/www/stickers

# Copy the service conf
cp systemd.service /etc/systemd/system/stickers.service

# Tweak the absolute path or other parameters if needed:
nano /etc/systemd/system/stickers.service

systemctl daemon-reload
systemctl enable stickers --now

# Check is is indeed running with
systemctl status stickers

# Same things for the printing worker daemon, if you enabled the print queue in .env
cp systemd-worker.service /etc/systemd/system/stickers-worker.service
# If needed, edit the conf with nano /etc/systemd/system/stickers-worker.service
systemctl daemon-reload
systemctl enable stickers-worker --now
systemctl status stickers-worker
```

### `nginx`

Having to type the local IP + port number is impractical for long term use. It's possible to tweak the flask/gunicorn command to listen to port 80, but this is not really a standard practice and there are other advantages in setting up a proper web server (possibly speed up the serving of static assets)

```
location / {
    proxy_pass http://unix:/var/www/stickers.local/sock;
}
location /assets {
    alias /var/www/stickers.local/assets/;
}
```

### access with a `.local` domain

To simplify access even further, you can install `avahi-daemon` on the server, and configure it to broadcast `stickers.local` (or `whatever.local`). This is called Bonjour Protocol, or MDNS. Note that not every client supports it though (typically not all smartphones may resolve .local domains, and maybe not all laptops eithers)

```
# In /etc/avahi/avahi-daemon.conf
[server]
host-name=stickers
```
