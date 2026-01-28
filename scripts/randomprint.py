import requests
import random
import os
from gpiozero import Button
from time import sleep

os.environ['BROTHER_QL_PRINTER'] = 'file:///dev/usb/lp0'
#os.environ['BROTHER_QL_MODEL'] = 'QL-720NW'
os.environ['BROTHER_QL_MODEL'] = 'QL-570'

button = Button(27)
rootdir = "/home/pi/stickers.local"

print("en attente d'appui")

os.system("pwd")

while True:
  if button.is_pressed:
    print('appuye')
    file = random.choice(os.listdir(rootdir+"/scripts/postprocessimg/memes/"))
    #file = random.choice(os.listdir("../assets/uploads/memesbadtrans/"))
    print(file)
    os.system(f'{rootdir}/venv/bin/brother_ql print -r90 -l 62 "{rootdir}/scripts/postprocessimg/memes/{file}"')
    url='http://localhost:5000/stickers/print?sticker=stickerbadtrans/'+file 
    print(url)
    query = requests.post(url)
    print(query.status_code)
  else:
    #print('relache')
    sleep(0.05)

