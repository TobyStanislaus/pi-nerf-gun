from time import sleep

def set_angle(angle, servo_pin, pi):
    pulse_width = int(500 + (angle / 180.0) * 2000)  # Convert angle to PWM pulse width
    pi.set_servo_pulsewidth(servo_pin, pulse_width)
    sleep(0.1)
    
    
def pull_switch(servo_pin, pi):
    set_angle(25, servo_pin, pi)
    set_angle(10, servo_pin, pi)
