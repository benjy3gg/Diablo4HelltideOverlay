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

def cleanup():
    print("Closing Browser...")
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
	
	# return the MSE, the lower the error, the more "similar"
	# the two images are
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

def send_message_to_ahk(message):
    print(message)
    with open('communication.txt', 'w') as file:
        file.write(message)



def convert(o):
    if isinstance(o, np.generic): return o.item()  
    raise TypeError
    
def capture_dx12_window(window_title):
    # Find the handle for the window named "filler"
    hwnd = win32gui.FindWindow(None, window_title)

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

    return img

def find_image_coordinates(main_image, template_image, factor=4):
    MIN_MATCH_COUNT = 10

    main_image = cv2.resize(main_image,(0,0), fx=1/factor, fy=1/factor)
    img1 = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
    img2 = cv2.cvtColor(main_image, cv2.COLOR_BGR2GRAY)
    kp1, des1 = sift.detectAndCompute(img1,None)
    kp2, des2 = sift.detectAndCompute(img2,None)

    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
    search_params = dict(checks = 20)

    flann = cv2.FlannBasedMatcher(index_params, search_params)
    #bf = cv2.BFMatcher()

    matches = flann.knnMatch(des1,des2,k=2)

    # store all the good matches as per Lowe's ratio test.
    good = []
    for m,n in matches:
        if m.distance < 0.7*n.distance:
            good.append(m)
    
    if len(good)>MIN_MATCH_COUNT:
        src_pts = np.float32([ kp1[m.queryIdx].pt for m in good ]).reshape(-1,1,2)
        dst_pts = np.float32([ kp2[m.trainIdx].pt for m in good ]).reshape(-1,1,2)

        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        matchesMask = mask.ravel().tolist()

        h,w = img1.shape
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
            "x": 0,
            "y": 0,
            "w": 0,
            "h": 0,
            #"r": rotation,
            "sx": 1,
            "sy": 1
        }
    return data

def main():
    global MWidth, MHeight, font_size, tracker, window_title, sift, main_image_path, template_image_path, ahk_process
    MWidth = GetSystemMetrics(0)
    MHeight = GetSystemMetrics(1)

    font_size = json.loads(open("settings.txt", "r").read())["fontsize"]

    print(f"Detected Resolution {MWidth},{MHeight}, FontSize: {font_size}")

    tracker = HelltideTracker()
    tracker.setup()
    print("Waiting for 5 seconds for initialization...")
    ahk_process = start_ahk()
    time.sleep(5)
    # Initialize the SIFT detector
    sift = cv2.SIFT_create()

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
    while True:
        try:
            debug = f"{tracker.chest_reset_timer()} "
            counter += 1
            map_open = is_map_open(window_title)
            if counter == 5:
                m,chests,events = tracker.take_screenshot()
            if counter % 20 == 0:
                is_helltide = tracker.is_helltide_active()
            if counter % 120 == 0:
                m,chests,events = tracker.take_screenshot()
            if map_open:
                debug = {"timer": tracker.when_is_next_helltide(), "debug": " Map is open |"}
                if is_helltide:
                    captured_image = capture_dx12_window(window_title)
                    diff = 0
                    if last_image is not None:
                        diff = mse(captured_image, last_image)
                    
                    if diff > 100:
                        template_image = cv2.imread(m)
                        data = find_image_coordinates(captured_image, template_image)
                        
                        aspect_ratio = abs(data["sx"]-data["sy"])
                        print(aspect_ratio)
                        if aspect_ratio > 0.3:
                            send_message_to_ahk(json.dumps(debug, default=convert, separators=(',', ':')))
                            continue
                        data["map_image"] = m
                        data["chests"] = []
                        data["events"] = []
                        print(chests)
                        print(events)
                        if chests:
                            for chest in chests:
                                data["chests"].append({"x": chest['x'], "y": chest['y'], "r": chest["r"]})
                        if events:
                            for event in events:
                                data["events"].append({"x": event['x'], "y": event['y'], "r": event["r"]})
                        data = data | debug
                        send_message_to_ahk(json.dumps(data, default=convert, separators=(',', ':')))
                    last_image = captured_image
                else:
                    send_message_to_ahk(json.dumps(debug, default=convert, separators=(',', ':')))
            else:
                debug += " Map is closed |"
                send_message_to_ahk(json.dumps(debug, default=convert, separators=(',', ':')))
            time.sleep(0.5)
        except KeyboardInterrupt:
            cleanup()

if __name__ == "__main__":   
    #SetConsoleCtrlHandler(lambda x: cleanup(), True)
    main()
