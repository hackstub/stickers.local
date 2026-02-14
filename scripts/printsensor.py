import requests
import random
import os
import RPi.GPIO as GPIO
import time
from gpiozero import Button
from time import sleep
import MotionSensor

#os.environ['BROTHER_QL_PRINTER'] = 'file:///dev/usb/lp0'
os.environ['BROTHER_QL_MODEL'] = 'QL-720NW'
#os.environ['BROTHER_QL_MODEL'] = 'QL-570'

#button = Button(27)

#----- code pour le capteur de mouvement-----
GPIO.setmode(GPIO.BCM)
capteur = MotionSensor(7)

GPIO.setup(capteur,GPIO.IN)
print ("démarrage du capteur")



while True:
  if capteur.motion_detected:
    print ("mouvement détecté")
  else:
    print ("en attente de passage")
    time.sleep(0.2)

for i in range(3):
    #print('appuye')
    #file = random.choice(os.listdir("./postprocessimg"))
  file = random.choice(os.listdir("../assets/uploads/memesbadtrans/"))
  print(file)
    #os.system(f'./venv/bin/brother_ql print -r90 -l 62 "./postprocessimg/{file}"')
  url='http://localhost:5000/stickers/print?sticker=stickerbadtrans/'+file 
  print (url)
  try:
    query = requests.post(url)
    print(query.status_code)
  except Exception as e:
    print("Erreur :",e)
    sleep(0.5)
sleep(2)

else:
    print ('pas de mouvement')
    time.sleep(2)



