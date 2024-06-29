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

(cd assets && bash fetch_assets)
```

And then start the dev server:

```bash
source venv/bin/activate
FLASK_APP=app.py FLASK_ENV=development flask --debug run
```
