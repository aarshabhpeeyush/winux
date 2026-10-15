-- WinUx Save Point: click the star to "save".

local LINES = {
  "* (The glow of your desktop fills you with determination.)",
  "* (Knowing your files are safe fills you with determination.)",
  "* (The hum of the fans fills you with determination.)",
  "* (Seeing your wallpaper move fills you with determination.)",
  "* (The taskbar is clean. It fills you with determination.)",
}

function Initialize()
  saving = 0
end

function Save()
  -- the save itself
  SKIN:Bang("!SetVariable", "Say", "File saved.")
  SKIN:Bang("!SetVariable", "SayColor", "255,230,0")
  local sound = SKIN:GetVariable("WinUxDir") .. "\\generated\\sounds\\save.wav"
  SKIN:Bang('[Play "' .. sound .. '"]')
  SKIN:Bang("!UpdateMeter", "MeterSay")
  SKIN:Bang("!Redraw")
  saving = 40   -- 4 seconds at Update=100
end

function Update()
  if saving > 0 then
    saving = saving - 1
    if saving == 0 then
      SKIN:Bang("!SetVariable", "Say", LINES[math.random(#LINES)])
      SKIN:Bang("!SetVariable", "SayColor", "255,255,255")
      SKIN:Bang("!UpdateMeter", "MeterSay")
      SKIN:Bang("!Redraw")
    end
  end
  return 0
end
