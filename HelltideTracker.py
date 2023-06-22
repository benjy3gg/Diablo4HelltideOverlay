import time
import cv2
import matplotlib.pyplot as plt
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


from PIL import Image
import numpy as np

class HelltideTracker:
    def __init__(self):
        self.last_helltide = ""
        self.browser = None

        #self.leaflet_fullscreen_css = open("leaflet/Control.FullScreen.css", "r").read()
        #self.leaflet_fullscreen_js = open("leaflet/Control.FullScreen.js", "r").read()
        #print(self.leaflet_fullscreen_js)

    def setup(self):
        # URL of the website
        URL = 'https://helltides.com/'

        # Element ID of the div to capture
        ELEMENT_ID = 'map'
        webdriver_options = Options()
        webdriver_options.page_load_strategy = 'eager'
        webdriver_prefs = {}
        webdriver_options.add_argument("--headless")
        webdriver_options.add_argument("--disable-gpu")
        webdriver_options.add_argument("--no-sandbox")
        webdriver_options.add_argument("--disable-dev-shm-usage")
        webdriver_options.add_argument("--window-size=2560,1440")
        #webdriver_options.add_argument("--app=https://helltides.com/")
        webdriver_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 7.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36")

        webdriver_options.add_experimental_option('excludeSwitches', ['enable-logging', "enable-automation"])
        webdriver_options.experimental_options["prefs"] = webdriver_prefs
        webdriver_prefs["profile.default_content_settings"] = {"images": 2}

        service = Service(ChromeDriverManager().install())
        self.browser = webdriver.Chrome(service=service, options=webdriver_options)
        self.browser.get(URL)
        self.browser.execute_script("window.maps = [];")
        #self.init_maps()
        time.sleep(.5)
        self.hide_all_shit()

    def init_maps(self):
         self.browser.execute_script("""
            (async() => {
                console.log("waiting for variable L");
                while(!window.hasOwnProperty("L"))
                    await new Promise(resolve => setTimeout(resolve, 10));
                window.L.Map.addInitHook(function () { window.maps.push(this); console.log(window.maps);});
            })();
                (async() => {
                console.log("waiting for variable L");
                while(!L)
                    await new Promise(resolve => setTimeout(resolve, 10));
                L.Map.addInitHook(function () { window.maps.push(this); console.log(window.maps);});
            })();
            (async() => {
                console.log("waiting for variable L");
                while(!window.maps[0])
                    await new Promise(resolve => setTimeout(resolve, 10));
                const image = Object.values(window.maps[0]._layers)[0]._image
                window.maps[0]._container.style.position = 'absolute';
                window.maps[0]._container.style.width = image.naturalWidth + 'px';
                window.maps[0]._container.style.height = image.naturalHeight + 'px';
                window.maps[0].invalidateSize(false);
                //window.maps[0].fitWorld();
            })();
        """)
        

    def hide_all_shit(self):
        try:
            #self.browser.execute_script("console.log(window.maps)")
            # L.Map.addInitHook(function () { window.maps.push(this); console.log(window.maps);}); 
            self.browser.execute_script("document.querySelector('html').style.visibility = 'hidden';")
            self.browser.execute_script("document.querySelector('#map').style.visibility = 'visible';")
            self.browser.execute_script("document.querySelector('.leaflet-control-container').style.visibility = 'hidden';")
            self.browser.execute_script("document.querySelector('#ad_feed_bottom').parentElement.style.display = 'none';")
            self.browser.execute_script("document.querySelector('nav').style.display = 'none';")
            self.browser.execute_script("document.querySelector('.max-w-screen-2xl .mx-auto').style.display = 'none';")
            self.browser.execute_script("document.querySelectorAll('#map .leaflet-interactive .rounded-full').forEach((e) => e.style.borderColor = '#ffcc00');")
            #time.sleep(.5)
        except Exception as e:
            print(e)
            pass

    def is_helltide_active(self):
        try:
            is_active = self.browser.execute_script("return !!document.querySelector('#map')")
            if is_active:
                self.browser.execute_script("document.querySelector('.flex .gap-2:has(svg)').click()")
            return is_active
        except Exception as e:
            print(e)
            return False

    def when_is_next_helltide(self):
        lines = []
        lines.append("const helltide = [...document.querySelectorAll('.text-2xl').values()].find((a) => a.textContent.includes('Helltide'))")
        lines.append("const helltide_text = helltide.textContent")
        lines.append("let helltide_timer = helltide.nextSibling.textContent")
        lines.append("helltide_timer = helltide_timer.replace(/(Mute Sound|\\n)/g, '')")
        lines.append("return '' + helltide_text + ': ' + helltide_timer")
        script = ";\n".join(lines)

        try:
            return self.browser.execute_script("""
                const helltide = [...document.querySelectorAll('.text-2xl').values()].find((a) => a.textContent.includes('Helltide'))
                const helltide_text = helltide.textContent
                let helltide_timer = helltide.nextSibling.textContent
                helltide_timer = helltide_timer.replace(/(Mute Sound|\\n)/g, '')
                return helltide_timer
            """)
        except Exception as e:
            print(e)
            pass
        
        
    def chest_reset_timer(self):
        try:
            return self.browser.execute_script('return document.querySelector("#voting-feed .cursor-pointer .text-sm").textContent')
        except:
            return ""
        

    def take_screenshot(self):
        if self.is_helltide_active():
            try:
                self.hide_all_shit()
            except:
                pass
            try:
                
                map = self.browser.find_element(By.ID,"map")

                map_name = f"images/maps/map.png"
                map_overlay_name = f"images/maps/overlay.png"

                map.screenshot(map_name)

                im = Image.open(map_name)
                im = im.convert('RGBA')

                data = np.array(im)
                red, green, blue, alpha = data.T

                # Replace white with red... (leaves alpha values alone...)
                #areas = ((red == 34) & (blue == 94) & (green == 197)) | ((red == 255) & (blue == 0) & (green == 204)) | ((205 < red) & (red < 235) & (175 < blue) & (blue < 
                #areas = ((red == 34) & (blue == 94) & (green == 197)) | ((red == 255) & (blue == 0) & (green == 204)) | ((205 < red) & (red < 235) & (175 < blue) & (blue < 200) & (195 < green) & (green < 230))
                areas = ((red == 34) & (blue == 94) & (green == 197)) | ((red == 255) & (blue == 0) & (green == 204))
                areas = np.invert(areas)
                data[...][areas.T] = (0, 0, 0, 0) # Transpose back needed

                im2 = Image.fromarray(data)
                im2.save(map_overlay_name)

                # Convert the image to grayscale
                gray = cv2.cvtColor(data, cv2.COLOR_BGR2GRAY)

                # Apply a blur to reduce noise (optional)
                gray = cv2.GaussianBlur(gray, (5, 5), 0)

                # Apply the Hough circle transform
                circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1, minDist=20,
                            param1=15, param2=15, minRadius=5, maxRadius=50)

                chests = []
                events = []
                # Ensure circles were found
                if circles is not None:
                    # Convert the circle parameters to integers
                    circles = np.round(circles[0, :]).astype(int)

                    # Loop over the detected circles
                    for (x, y, r) in circles:
                        if r < 10:
                            chests.append({"x": x, "y": y, "r": r})
                        else:
                            events.append({"x": x, "y": y, "r": r})
                else:
                    pass

                return map_name, chests, events
            except Exception as e:
                print(e)
                return None, None, None
        else:
            print('Not taking screenshot, helltide is not active!!!')
            return None, None, None
        
                
    def get_browser(self):
        return self.browser