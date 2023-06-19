#NoEnv
#SingleInstance force
#Persistent
#Include Gdip_All.ahk
#Include CustomFont.ahk
#Include Jxon.ahk
#MaxThreads 1

DetectHiddenWindows, on

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

Width := A_ScreenWidth, Height := A_ScreenHeight
OptionsTimer := "x1p y30 w" . Width . " Left cddffffff r4 s20"
OptionsDebug := "x0 y30 w" . Width . " Right cddffff00 r4 s20"

; Create a layered window (+E0x80000 : must be used for UpdateLayeredWindow to work!) that is always on top (+AlwaysOnTop), has no taskbar entry or caption
Gui, 1: -Caption +E0x80000 +E0x20 +LastFound +AlwaysOnTop +ToolWindow +OwnDialogs
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

Loop
{
    ;Gui, 1: Show, NA
    FileRead jsonString, communication.txt
    Data := Jxon_Load(jsonString)

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

    overlay := Data.overlay_image
    refresh := Data.refresh

    Gdip_GraphicsClear(G)

    String := Format("{1:s}", helltidetimer)
    FontName := A_WorkingDir . "\Diablo.ttf"
    Gdip_TextToGraphics(G, string, OptionsTimer, FontName, Width, Height)
    Gdip_TextToGraphics(G, debug, OptionsDebug, FontName, Width, Height)

    ; Draw chests, scale and move according to sx, sy, x, y
    for index, chest in chests {
        gdip_DrawEllipse(G, greenPen, x + (chest.x * sx) - (10 * sx), y + (chest.y * sy), chest.r * sx * 2, chest.r * sx * 2)
    }

    ; Draw events, scale and move according to sx, sy, x, y
    for index, event in events {
        gdip_DrawEllipse(G, orangePen, x + (event.x * sx) - (10 * sx), y + (event.y * sy) - (10 * sy) , event.r * sx * 2, event.r * sx * 2)
    }

    UpdateLayeredWindow(hwnd1, hdc, 0, 0, Width, Height)

    Sleep, 50
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
Return
