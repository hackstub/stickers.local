import requests
import random
import os
from gpiozero import Button
from time import sleep

os.environ['BROTHER_QL_PRINTER'] = 'file:///dev/usb/lp0'
os.environ['BROTHER_QL_MODEL'] = 'QL-720NW'
os.environ['BROTHER_QL_MODEL'] = 'QL-570'

button = Button(27)
rootdir = "/home/pi/stickers.local"
imagesdir = rootdir + "/assets/uploads"

print("en attente d'appui")

os.system("pwd")

while True:
   if button.is_pressed:
     print('appuye')
     for collection in sorted(os.listdir(imagesdir+"/postprocessimg")):
         print(collection)
         file = random.choice(os.listdir(imagesdir+"/postprocessimg/"+collection))
         print(file)
         os.system("echo 'printing " + file + "'")
         os.system(rootdir + '/venv/bin/brother_ql print -l 62 '+ imagesdir + '/postprocessimg/' + collection + '/' + file)
         os.system("qrterminal " + file)
   else:
     #print('relache')
     sleep(0.05)

