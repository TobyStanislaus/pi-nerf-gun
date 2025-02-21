import RPi.GPIO as GPIO
from time import sleep

def set_angle(angle, servo_pin, pwm):
    duty = 2+(angle/18)
    GPIO.output(servo_pin, True)
    pwm.ChangeDutyCycle(duty)
    sleep(0.5)
    GPIO.output(servo_pin, False)
    pwm.ChangeDutyCycle(0)
    
    
def pull_switch(servo_pin, pwm):
    set_angle(15, servo_pin, pwm)
    sleep(0.5)
    set_angle(0, servo_pin, pwm)
