import base64
import glob
import json
import os
import time
from ctypes import windll
import subprocess

import cv2
import numpy as np
import win32gui
import win32ui
from win32api import GetSystemMetrics, SetConsoleCtrlHandler

from HelltideTracker import HelltideTracker
from python_imagesearch.imagesearch import imagesearcharea

import cProfile, pstats
import configparser    

def cleanup():
    print("Closing Browser...")
    tracker.get_browser().close()
    tracker.get_browser().quit()
    print("Closing UI...")
    ahk_process.terminate()
    quit()

def start_ahk():
    # Start the secondary script
    return subprocess.Popen(['./d4gui.exe'])


def mse(imageA, imageB):
    # the 'Mean Squared Error' between the two images is the
    # sum of the squared difference between the two images;
    # NOTE: the two images must have the same dimension
	err = np.sum((imageA - imageB))
	err /= float(imageA.shape[0] * imageA.shape[1])
	return err   
    

def get_latest_images():
    list_of_files_map = glob.glob('images/maps/*_map.png') # * means all i  f need specific format then *.csv
    sorted_files_map = sorted(list_of_files_map, key=os.path.getctime)

    list_of_files_overlay = glob.glob('images/maps/*_overlay.png') # * means all i  f need specific format then *.csv
    sorted_files_overlay = sorted(list_of_files_overlay, key=os.path.getctime)
    return "images/maps/map.png", "images/maps/overlay.png"
    return sorted_files_map[-1], sorted_files_overlay[-1]



def is_map_open(window_title=None):
    if window_title:
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            map_image = f"images/map_{MHeight}_{font_size}.png"
            pos = imagesearcharea(map_image, MWidth//4, 0, MWidth//2, 128, 0.94)
            if pos[0] != -1:
                return True
            else:
                return False
        else:
            return False
    else:
        return False

def send_message_to_ahk(data):
    message = json.dumps(data, default=convert, separators=(',', ':'))
    with open('communication.txt', 'w') as file:
        file.write(message)

def convert(o):
    if isinstance(o, np.generic): return o.item()
    raise TypeError
    
def capture_dx12_window(window_title):
    # Find the handle for the window named "filler"
    hwnd = win32gui.FindWindow(None, window_title)
    if hwnd:

        # Get the dimensions of the window
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        w = right - left # set size here if you want
        h = bottom - top # set size here if you want 

        # Create a device context (DC) for the window
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        dc = mfcDC.CreateCompatibleDC()

        # Create a bitmap object and select it into the device context
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(mfcDC, w, h)
        dc.SelectObject(bmp)
        
        # Take Screenshot
        windll.user32.PrintWindow(hwnd, dc.GetSafeHdc(), 2)
        
        # Convert the bitmap object to a numpy array
        signedIntsArray = bmp.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype='uint8')
        img.shape = (h, w, 4)

        # Clean up
        dc.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        win32gui.DeleteObject(bmp.GetHandle())

        clones_b64 = {}
        for clone in clones:
            crop = img[clone["y"]:clone["h"], clone["x"]:clone["w"]]
            _, buffer = cv2.imencode('.png', crop)
            b64 = base64.b64encode(buffer).decode("utf-8")
            clones_b64[clone["clonename"]] = b64
            #cv2.imwrite(f'images/clones/{clone["clonename"]}.png', crop)
        return img, clones_b64
    else:
        return None

def resize_image(image, target_height=720):

    # Get the original image's width and height
    original_height, original_width = image.shape[:2]

    # Calculate the aspect ratio
    factor = target_height / original_height

    # Calculate the new width while maintaining the aspect ratio
    target_width = int(original_width * factor)

    # Resize the image
    resized_image = cv2.resize(image, (target_width, target_height))

    return resized_image, factor

def find_image_coordinates(main_image, template_image, kp1, des1, factor=6):
    MIN_MATCH_COUNT = 10

    main_image = cv2.resize(main_image,(0,0), fx=1/factor, fy=1/factor)
    #main_image, factor = resize_image(main_image)
    
    img2 = cv2.cvtColor(main_image, cv2.COLOR_BGR2GRAY)
    
    kp2, des2 = sift.detectAndCompute(img2,None)

    matches = flann.knnMatch(des1,des2,k=2)

    # store all the good matches as per Lowe's ratio test.
    good = []
    for m,n in matches:
        if m.distance < 0.7*n.distance:
            good.append(m)
    
    if len(good)>MIN_MATCH_COUNT:
        src_pts = np.float32([ kp1[m.queryIdx].pt for m in good ]).reshape(-1,1,2)
        dst_pts = np.float32([ kp2[m.trainIdx].pt for m in good ]).reshape(-1,1,2)

        M, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

        h,w = template_image.shape
        pts = np.float32([ [0,0],[0,h-1],[w-1,h-1],[w-1,0] ]).reshape(-1,1,2)
        dst = cv2.perspectiveTransform(pts,M)

        main_image_coordinates = np.int32(dst)

        # Calculate rotation and scale factors
        scale_x = np.linalg.norm(M[:, 0])
        scale_y = np.linalg.norm(M[:, 1])
        #rotation = np.arctan2(M[1, 0], M[0, 0]) * 180.0 / np.pi

        x, y, w, h = cv2.boundingRect(main_image_coordinates)

        data = {
            "x": x*factor,
            "y": y*factor,
            "w": w*factor,
            "h": h*factor,
            #"r": rotation,
            "sx": scale_x*factor,
            "sy": scale_y*factor
        }

    else:
        print( "Not enough matches are found - {}/{}".format(len(good), MIN_MATCH_COUNT) )
        data = data = {
            "x": -1000,
            "y": -1000,
            "w": 0,
            "h": 0,
            #"r": rotation,
            "sx": 1,
            "sy": 1
        }
    return data


def calc_template_features(template_image):
    img1 = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
    kp1, des1 = sift.detectAndCompute(img1,None)
    return img1, kp1, des1

def process_new_map():
    print("Updating Map from helltides.com")
    m,chests,events = tracker.take_screenshot()
    if m:
        template_image = cv2.imread(m)
        template_image, kp1, des1 = calc_template_features(template_image)
        print("Got helltides")
        return template_image, kp1, des1, chests, events
    else:
        return None, None, None, None, None
    
def read_ini(ini_name='settings.ini'):
    clones = []
    config = configparser.ConfigParser()
    config.read('settings.ini', encoding='utf-16')
    for section in config.sections():
        if section.startswith("clone"):
            clone = {}
            for (key, value) in config.items(section):
                if key != "clonename":
                    clone[key] = int(value)
                else:
                    clone[key] = value
            clones.append(clone)
    return clones

def main():
    global MWidth, MHeight, font_size, tracker, window_title, sift, main_image_path, template_image_path, ahk_process, flann, clones
    MWidth = GetSystemMetrics(0)
    MHeight = GetSystemMetrics(1)

    clones = read_ini()

    font_size = json.loads(open("settings.txt", "r").read())["fontsize"]

    print(f"Detected Resolution {MWidth},{MHeight}, FontSize: {font_size}")

    tracker = HelltideTracker()
    tracker.setup()
    print("Waiting for 5 seconds for initialization...")
    ahk_process = start_ahk()
    time.sleep(5)
    # Initialize the SIFT detector
    sift = cv2.SIFT_create(nfeatures = 3000)
    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
    search_params = dict(checks = 20)
    flann = cv2.FlannBasedMatcher(index_params, search_params)

    last_image = None
    # Usage example
    main_image_path = 'path_to_main_image.jpg'
    template_image_path = 'path_to_template_image.jpg'


    # Usage example
    window_title = 'Diablo IV'
    chests = []
    events = []

    counter = 0
    is_helltide = False
    last_data = {}
    map_open = False
    print("Starting Loop")
    next_helltide = tracker.when_is_next_helltide()
    chest_timer_text = ""
    clones_b64 = []
    while True:
        try:
            data = {"timer": next_helltide, "debug": chest_timer_text}
            counter += 1
            captured_image, clones_b64 = capture_dx12_window(window_title)
            if counter % 5 == 0:
                chest_timer_text = tracker.chest_reset_timer()
                map_open = is_map_open(window_title)
                next_helltide = tracker.when_is_next_helltide()
            if counter == 5:
                data["debug"] += "Starting"
                template_image, kp1, des1, chests, events = process_new_map()
            if counter % 20 == 0:
                #clones = read_ini()
                is_helltide = tracker.is_helltide_active()
            if counter % 120 == 0:
                if is_helltide:
                    template_image, kp1, des1, chests, events = process_new_map()
            if map_open:
                data["debug"] += f" Map Open"
                if is_helltide:
                    start = time.time()
                    endCapture = time.time() - start
                    data["debug"] += f"C: {'{:.4f}'.format(endCapture)}"
                    diff = 0
                    if last_image is not None:
                        diff = mse(captured_image, last_image)
                    if diff > 100:
                        start = time.time()
                        data = data | find_image_coordinates(captured_image, template_image, kp1, des1)
                        endFind = time.time() - start
                        data["debug"] += f"F: {'{:.4f}'.format(endFind)}"
                        aspect_ratio = abs(data["sx"]-data["sy"])
                        if aspect_ratio > 0.3:
                            send_message_to_ahk(data)
                            last_image = captured_image
                            continue
                        #data["map_image"] = m
                        data["chests"] = []
                        data["events"] = []

                        if chests:
                            for chest in chests:
                                data["chests"].append({"x": chest['x'], "y": chest['y'], "r": chest["r"]})
                        if events:
                            for event in events:
                                data["events"].append({"x": event['x'], "y": event['y'], "r": event["r"]})
                        last_data = data
                    else:
                        data = last_data
                        last_data["timer"] = next_helltide
                    last_image = captured_image
                else:
                    last_data = {} 
            else:
                data["clones"] = clones_b64

            send_message_to_ahk(data)
            
        except KeyboardInterrupt:
            cleanup()
        except Exception as e:
            print("Exception", e)
        finally:
            time.sleep(0.1)

if __name__ == "__main__":   
    #SetConsoleCtrlHandler(lambda x: cleanup(), True)
    main()
