# D4 Helltide Overlay

## Configuration
- Edit settings.txt and set your fontsize to your ingame "Font Scale", "small" "medium" or "large"

## How to start
- Open the D4Overlay.exe and let it run for a while
- If you go to the Ingame-Map you will see an info text in the top left indicating either a Helltide running or when the next one will start
- move your map to the helltide-area and after a while you should see circles appearing on your screen. 
	- green circles indicate the mystic helltide boxes
	- orange circles indicate the area where an event can start

## How it works
- 3 modules
	- Chrome headless-browser opening https://helltides.com
	- Python script that extracts information from the website (D4Overlay.exe)
	- Autohokey GUI that displays the data as an overlay (ahk.exe)

## Important!
- To close the program correctly, press ctrl+c in the terminal window and wait for the window to close. Otherwise the Python, AHK or browser executables might not close correctly 

## Credits
- Helltides.com for providing the information
