-- WinUx Calendar: fills the 6x7 grid for this month and puts the soul on today.

-- must match the grid in Calendar.ini
local X0, CW, Y0, RH = 46, 40, 96, 30

local MONTHS = { "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
                 "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER" }

function Initialize()
  shown = ""
end

function Update()
  local now = os.date("*t")
  local key = now.year .. "-" .. now.month .. "-" .. now.day
  if key == shown then return 0 end
  shown = key

  local first = os.date("*t", os.time({ year = now.year, month = now.month, day = 1, hour = 12 }))
  local days = os.date("*t", os.time({ year = now.year, month = now.month + 1, day = 0, hour = 12 })).day
  local offset = first.wday - 1          -- 0 = the month starts on Sunday

  SKIN:Bang("!SetOption", "MeterMonth", "Text", "* " .. MONTHS[now.month] .. " " .. now.year)
  for cell = 1, 42 do
    local d = cell - offset
    local text = (d >= 1 and d <= days) and tostring(d) or ""
    SKIN:Bang("!SetOption", "Day" .. cell, "Text", text)
    SKIN:Bang("!SetOption", "Day" .. cell, "FontColor", d == now.day and "255,255,255,255" or "#Line#")
  end

  -- the soul sits behind today (heart is 34x29 once scaled)
  local cell = now.day + offset - 1
  local r, c = math.floor(cell / 7), cell % 7
  SKIN:Bang("!SetVariable", "TodayX", X0 + c * CW + 12 - 17)
  SKIN:Bang("!SetVariable", "TodayY", Y0 + r * RH - 1)
  SKIN:Bang("!UpdateMeter", "*")
  SKIN:Bang("!Redraw")
  return 1
end
