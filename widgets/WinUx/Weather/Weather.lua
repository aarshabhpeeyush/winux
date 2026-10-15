-- WinUx Weather: turns the weather into a Spamton sales pitch.

local LINES = {
  "* HEY [[Little Sponge]]! THE CURRENT WEATHER IS [[%s]]!! IT'S [[%s]] OUTSIDE!",
  "* NOW'S YOUR CHANCE TO BE A [[Big Shot]]! THE SKY SAYS [[%s]] AND [[%s]]!",
  "* [[Hot Single]] WEATHER IN YOUR AREA: [[%s]], [[%s]]!! CLICK NOW!!",
  "* DON'T FORGET YOUR [[Umbrella]]... OR DO! IT'S [[%s]] AND [[%s]]!",
  "* KRIS!! THE WEATHER IS [[%s]]! [[%s]]! [[Deals]] SO GOOD I'LL [[Shiver]]!",
  "* ACT NOW! [[Limited Time]] WEATHER: [[%s]] AT ONLY [[%s]]!!!",
  "* THE FORECAST IS [[%s]]. THE TEMPERATURE IS [[%s]]. [[Hyperlink Blocked]].",
}

function Initialize()
  last = 0
end

function Pick()
  local cond = SKIN:GetMeasure("MeasureCondition"):GetStringValue()
  local temp = SKIN:GetMeasure("MeasureTemp"):GetStringValue()
  if cond == nil or cond == "" then return end
  local n = math.random(#LINES)
  if n == last then n = n % #LINES + 1 end
  last = n
  local text = string.format(LINES[n], string.upper(cond), temp)
  SKIN:Bang("!SetVariable", "Pitch", text)
  SKIN:Bang("!UpdateMeter", "MeterLine")
  SKIN:Bang("!Redraw")
end

function Update()
  return 0
end
