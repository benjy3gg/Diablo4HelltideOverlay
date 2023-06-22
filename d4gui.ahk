#NoEnv
#SingleInstance force
#Persistent
#Include Gdip_All.ahk
#Include CustomFont.ahk
#Include Jxon.ahk

SetTitleMatchMode, 2 ; Match any window title containing "Diablo IV"
DetectHiddenWindows, on

global clonex := -1
global cloney := -1
global clonew := -1
global cloneh := -1
global clonedx := -1
global clonedy := -1

; Start GDI+
If !pToken := Gdip_Startup()
{
    MsgBox, 48, gdiplus error!, Gdiplus failed to start. Please ensure you have gdiplus on your system
    ExitApp
}
OnExit, Exit

Font := "Diablo"
If !hFamily := Gdip_FontFamilyCreate(Font)
{
    MsgBox, 48, Font error!, The font you have specified does not exist on the system
    ExitApp
}
Gdip_DeleteFontFamily(hFamily)

pBitmapChest := Gdip_CreateBitmapFromFile("images/icons/mysterious_chest_green.png")
pBitmapEvent := Gdip_CreateBitmapFromFile("images/icons/events_icon.png")

Width := A_ScreenWidth, Height := A_ScreenHeight
OptionsTimer := "x1p y30 w" . Width . " Left cddffffff r4 s20"
OptionsDebug := "x0 y30 w" . Width . " Right cddffff00 r4 s20"

; Create a layered window (+E0x80000 : must be used for UpdateLayeredWindow to work!) that is always on top (+AlwaysOnTop), has no taskbar entry or caption
Gui, 1: -Caption +E0x80000 +E0x22 +LastFound +AlwaysOnTop +ToolWindow +OwnDialogs
; Show the window
Gui, 1: Show, NA
; Get a handle to this window we have created in order to update it later
hwnd1 := WinExist()
; Create a GDI bitmap with width and height of the drawing area
hbm := CreateDIBSection(Width, Height)
; Get a device context compatible with the screen
hdc := CreateCompatibleDC()
; Select the bitmap into the device context
obm := SelectObject(hdc, hbm)
; Get a pointer to the graphics of the bitmap for drawing
G := Gdip_GraphicsFromHDC(hdc)
; Set the smoothing mode to antialias = 4 to make shapes appear smoother
Gdip_SetSmoothingMode(G, 4)

greenPen := Gdip_CreatePen(0xff45f248, 3)
orangePen := Gdip_CreatePen(0xfffb923c, 3)
redPen := Gdip_CreatePen(0xffff0000, 3)
whitePen := Gdip_CreatePen(0xffffffff, 3)
showUI := true

settingsFilePath := "settings.ini"

IniRead, sections, Filename
ini := iniObj("settings.ini")

FontName := A_WorkingDir . "\Diablo.ttf"

GetRunningWindowText(window_title) {
    MouseGetPos,,,WindowUnderMouse
    WinGetTitle, title, ahk_id %WindowUnderMouse%
    Return title == window_title
}

list_files(Directory)
{
	files =
	Loop %Directory%\*.*
	{
		files = %files%`n%A_LoopFileName%
	}
	return files
}

iniObj(iniFile) {
    ini := []
    IniRead, sections,% inifile
    for number, section in StrSplit(sections,"`n") {
        IniRead, keys  ,% inifile,% section
        ini[section] := []
        for number, key in StrSplit(keys,"`n") {
            ini[section][StrSplit(key,"=").1] := StrSplit(key,"=").2
            }
        }
    Return ini
}

GdipCreateFromBase64(ByRef Base64, HICON := 0) {
	If (!DllCall("Crypt32.dll\CryptStringToBinary", "Ptr", &Base64, "UInt", 0, "UInt", 0x01, "Ptr", 0, "UIntP", DecLen, "Ptr", 0, "Ptr", 0)) {
		return False
	}

	VarSetCapacity(Dec, DecLen, 0)

	If (!DllCall("Crypt32.dll\CryptStringToBinary", "Ptr", &Base64, "UInt", 0, "UInt", 0x01, "Ptr", &Dec, "UIntP", DecLen, "Ptr", 0, "Ptr", 0)) {
		return False
	}

	pStream := DllCall("Shlwapi.dll\SHCreateMemStream", "Ptr", &Dec, "UInt", DecLen, "UPtr")
	DllCall("Gdiplus.dll\GdipCreateBitmapFromStreamICM", "Ptr", pStream, "PtrP", pBitmap)

	If (HICON) {
		DllCall("Gdiplus.dll\GdipCreateHICONFromBitmap", "Ptr", pBitmap, "PtrP", hBitmap, "UInt", 0)
	}

	ObjRelease(pStream)

	return (HICON ? hBitmap : pBitmap)
}

render_section(section, G, b64)
{
    filename := Format("images/clones/{1}.png", section.cloneName)
    if !pBitmap := GdipCreateFromBase64(b64)
    {
        ; MsgBox, error
    }else {
        Width := Gdip_GetImageWidth(pBitmap), Height := Gdip_GetImageHeight(pBitmap)
        Gdip_DrawImage(G, pBitmap, section.dx, section.dy, Width, Height)
        Gdip_DisposeBitmap(pBitmap)
    }
}


Loop
{
    FileRead jsonString, communication.txt
    Data := Jxon_Load(jsonString)

    active := GetRunningWindowText("Diablo IV")

    if active and showUI
    {
        for section, value in ini {
            b64 := Data.clones[value.cloneName]
            render_section(value, G, b64)
        }
        x := Data.x
        y := Data.y
        w := Data.w
        h := Data.h
        sx := Data.sx
        sy := Data.sy
        debug := Data.debug
        helltidetimer := Data.timer
        chests := Data.chests
        events := Data.events

        String := Format("{1:s}", helltidetimer)
        Gdip_TextToGraphics(G, string, OptionsTimer, FontName, Width, Height)
        Gdip_TextToGraphics(G, debug, OptionsDebug, FontName, Width, Height)

        for index, event in events {
            posy := y + (event.y * sy)
            if(posy > 100)
            {
                Gdip_DrawImage(G, pBitmapEvent, x + (event.x * sx) - 48/3, y + (event.y * sy) - 48/3, 48, 48)
                ;gdip_DrawEllipse(G, orangePen, x + (event.x * sx) - (10 * sx), y + (event.y * sy) - (10 * sy) , event.r * sx * 2, event.r * sx * 2)
            }
        }

        ; Draw chests, scale and move according to sx, sy, x, y
        for index, chest in chests {
            posy := y + (chest.y * sy)
            if posy > 100
            {
                Gdip_DrawImage(G, pBitmapChest, x + (chest.x * sx) - 48/3, y + (chest.y * sy) + (8*sy), 48, 48)
                ;gdip_DrawEllipse(G, greenPen, x + (chest.x * sx) - (9 * sx), y + (chest.y * sy) + (5 * sx), chest.r * sx * 2, chest.r * sx * 2)
            }
        }

        ; Draw events, scale and move according to sx, sy, x, y


        ; UpdateLayeredWindow(hwnd1, hdc, 0, 0, Width, Height)
    }else {
        ; Gdip_GraphicsClear(G)
    }
    UpdateLayeredWindow(hwnd1, hdc, 0, 0, Width, Height)
    Gdip_GraphicsClear(G)

    Sleep, 20
}

F1::
{
    MouseGetPos , clonex, cloney
    return
}

F2::
{
    MouseGetPos , clonew, cloneh
    return
}

F3::
{
    MouseGetPos , clonedx, clonedy
    MsgBox, x%clonex% y%cloney% w%clonew% h%cloneh% dx%clonedx% dy%clonedy%
    if (clonex > 0 and cloney > 0 and clonew > 0 and cloneh > 0)
    {
        InputBox, cloneName, Enter Identifier, (your input will be hidden)
        if ErrorLevel
        {
            MsgBox, CANCEL was pressed.
            return
        }
        else
        {
            MsgBox, You entered "%cloneName%"
        }

        IniWrite, %clonex%, settings.ini, clone_%cloneName%, x
        IniWrite, %cloney%, settings.ini, clone_%cloneName%, y

        IniWrite, %clonew%, settings.ini, clone_%cloneName%, w
        IniWrite, %cloneh%, settings.ini, clone_%cloneName%, h

        IniWrite, %clonedx%, settings.ini, clone_%cloneName%, dx
        IniWrite, %clonedy%, settings.ini, clone_%cloneName%, dy

        IniWrite, %cloneName%, settings.ini, clone_%cloneName%, cloneName

        clonex := -1
        cloney := -1
        clonew := -1
        cloneh := -1
        clonedx := -1
        clonedy := -1
        IniRead, sections, Filename
        ini := iniObj("settings.ini")
    }
    else
    {
        MsgBox, ERROR
        clonedx := -1
        clonedy := -1
        IniRead, sections, Filename
        ini := iniObj("settings.ini")
    }

    return
}

F4::
{
    showUI := !showUI
    return
}


Exit:
; Release resources
Gdip_DeletePen(greenPen)
Gdip_DeletePen(orangePen)
Gdip_DeletePen(redPen)
Gdip_DeletePen(whitePen)
Gdip_DeleteGraphics(G)
SelectObject(hdc, obm)
DeleteObject(hbm)
DeleteDC(hdc)
Gdip_DeleteFontFamily(hFamily)
Gdip_Shutdown(pToken)
ExitApp
