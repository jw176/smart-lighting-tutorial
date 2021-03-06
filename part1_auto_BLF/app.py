from rpi_ws281x import PixelStrip, Color
import math
import time
import datetime
import logging
import requests
import json
import constants # a file called constants.py that you need to put in the same directory as app.py

# LED strip configuration:
LED_COUNT = 119        # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
# LED_PIN = 10        # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

# Create NeoPixel object with appropriate configuration.
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
# Intialize the library (must be called once before other functions).
strip.begin()

def display_colour(red, green, blue):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(red, green, blue))
        strip.show() # if you don't want the effect of each pixel changing one by one, move this to after the for loop


def clamp(n, minn, maxn):
    # Function for limiting a number to a specified number range
    return max(min(maxn, n), minn)


def convertTempToRGB(temp):
    # Function for converting a colour temperature in Kelvin (K) to RGB
    # Algorithm from: https://tannerhelland.com/2012/09/18/convert-temperature-rgb-algorithm-code.html

    temp = temp / 100
    red = 0
    green = 0
    blue = 0

    # RED
    if temp <= 66:
        red = 255
    else:
        red = temp - 60
        red = 329.698727446 * (red ** -0.1332047592)
        red = clamp(red, 0, 255)

    # GREEN
    if temp <= 66:
        green = temp
        green = 99.4708025861 * math.log(green) - 161.1195681661
        green = clamp(green, 0, 255)
    else:
        green = temp - 60
        green = 288.1221695283 * (green ** -0.0755148492)
        green = clamp(green, 0, 255)

    # BLUE
    if temp >= 66:
        blue = 255
    else:
        if temp <= 19:
            blue = 0
        else:
            blue = temp - 10
            blue = 138.5177312231 * math.log(blue) - 305.0447927307
            blue = clamp(blue, 0, 255)

    # return (red, green, blue)
    return (round(red), round(green), round(blue))


# def get_current_temp(time, Max=4000, Min=650, slope=2, sunset=(20, 0), sunrise=(6, 0)):
#     time = time[0] + time[1]/60
#     sunset = sunset[0] + sunset[1]/60
#     sunrise = sunrise[0] + sunrise[1]/60

#     if time < (sunset - 24 + sunrise)/2:
#         return round(((Min - Max)/math.pi) * math.atan(slope * (time + 24 - sunset)) + (Max + Min)/2)
#     elif time < (sunrise + sunset) / 2:
#         return round(((Min - Max)/math.pi) * math.atan(-slope * (time - sunrise)) + (Max + Min)/2)
#     elif time < (sunset - 24 + sunrise)/2 + 24 :
#         return round(((Min - Max)/math.pi) * math.atan(slope * (time - sunset)) + (Max + Min)/2)
#     else:
#         return round(((Min - Max)/math.pi) * math.atan(-slope * (time - (sunrise + 24))) + (Max + Min)/2)


def get_current_temp(time, Max=4000, Min=650, hours=2, sunset=(20, 0), sunrise=(6, 0)):
    # Function for getting the relevant colour temperature for a the time of day
    # times are converted from a tuple (hour, minute) to a float
    time = time[0] + time[1]/60
    sunset = sunset[0] + sunset[1]/60
    sunrise = sunrise[0] + sunrise[1]/60

    n = math.pi / hours

    if time < sunrise - hours/2:
        return Min
    elif time < sunrise + hours/2:
        return ((Max - Min) / 2) * math.sin(n * (time - sunrise)) + ((Max + Min) / 2)
    elif time < sunset - hours/2:
        return Max
    elif time < sunset + hours/2:
        return -1 * ((Max - Min) / 2) * math.sin(n * (time - sunset)) + ((Max + Min) / 2) 
    else:
        return Min


def get_sunset_sunrise_time():
    # Function for getting the relevant sunrise and sunset times for your city
    city = constants.CITY
    api_key = constants.API_KEY

    response = requests.get(f"https://api.ipgeolocation.io/astronomy?apiKey={api_key}&location={city}")
    
    response = json.loads(response.content)
    sunrise = response["sunrise"]
    sunset = response["sunset"]
    date = response["date"]

    logging.info(f"Today's date: {date}, sunrise: {sunrise}, sunset: {sunset}")

    sunrise = sunrise.split(":")
    sunrise = (int(sunrise[0]), int(sunrise[1]))

    sunset = sunset.split(":")
    sunset = (int(sunset[0]), int(sunset[1]))

    return {"sunrise": sunrise, "sunset": sunset}


if __name__ == "__main__":
    format = "%(asctime)s [%(levelname)s]: %(message)s "
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")

    day = datetime.datetime.now().day # getting the current day
    results = get_sunset_sunrise_time()
    sunrise = results["sunrise"]
    sunset = results["sunset"]

    while True:
        currentDT = datetime.datetime.now() # getting the current time
        currentDT = (currentDT.hour, currentDT.minute)

        temp = get_current_temp(currentDT, sunrise=sunrise, sunset=sunset, hours=1.5) # getting current colour temperature
        red, green, blue = convertTempToRGB(temp) # converting current colour temperature to RGB
        display_colour(red, green, blue) # displaying RGB values on the led strip
        logging.info(f"Colour temperature = {temp},  red={red}, green={green}, blue={blue}")

        time.sleep(60) # this adjusts how often to update the colours of the lights

        if datetime.datetime.now().day != day:
            # its a new day
            # request sunset and sunrise times
            try:
                results = get_sunset_sunrise_time()
                sunrise = results["sunrise"]
                sunset = results["sunset"]
            except:
                logging.error('Could not retrieve sunrise and sunset information!')
                pass
