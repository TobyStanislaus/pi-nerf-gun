from time import sleep

PULL_ANGLE = 25
REST_ANGLE = 10


def set_angle(angle, servo_pin, pi):
    if not pi.connected:
        raise RuntimeError("pigpio daemon not connected - is pigpiod running?")
    pulse_width = int(500 + (angle / 180.0) * 2000)  # Convert angle to PWM pulse width
    pi.set_servo_pulsewidth(servo_pin, pulse_width)
    sleep(0.1)


def pull_switch(servo_pin, pi):
    set_angle(PULL_ANGLE, servo_pin, pi)
    set_angle(REST_ANGLE, servo_pin, pi)
