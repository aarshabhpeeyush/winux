-- WinUx Annoying Dog: walks along the bottom of the screen, naps, barks when clicked.
-- Runs 10 times a second (Update=100).

local W, H = 51, 66          -- the skin's size (dog image is 51x45 plus room for a bubble)
local SPEED = 2              -- pixels per tick

function Initialize()
  left = tonumber(SKIN:GetVariable("WORKAREAX")) or 0
  top = tonumber(SKIN:GetVariable("WORKAREAY")) or 0
  width = tonumber(SKIN:GetVariable("WORKAREAWIDTH")) or 1920
  height = tonumber(SKIN:GetVariable("WORKAREAHEIGHT")) or 1040
  x = left + math.random(0, math.max(1, width - W))
  dir = math.random(2) == 1 and 1 or -1
  state, timer, tick, said = "walk", math.random(40, 120), 0, 0
end

local function set(var, value)
  SKIN:Bang("!SetVariable", var, value)
end

local function say(text, ticks)
  set("Say", text)
  said = ticks
end

function Pet()
  -- click: it barks and hops (and wakes up)
  say("BARK!", 15)
  local sound = SKIN:GetVariable("WinUxDir") .. "\\generated\\sounds\\blip.wav"
  SKIN:Bang('[Play "' .. sound .. '"]')
  state, timer = "hop", 6
end

function Update()
  tick = tick + 1
  local y = top + height - H

  if state == "walk" then
    x = x + dir * SPEED
    if x < left then x, dir = left, 1 end
    if x > left + width - W then x, dir = left + width - W, -1 end
    set("Frame", (math.floor(tick / 3) % 2 == 0) and "dog-walk1" or "dog-walk2")
    -- the sprite faces left, so mirror it when walking right
    set("Flip", dir > 0 and "Horizontal" or "None")
    timer = timer - 1
    if timer <= 0 then
      if math.random(3) == 1 then dir = -dir end
      state, timer = "nap", math.random(60, 200)
    end
  elseif state == "nap" then
    set("Frame", "dog-sleep")
    if said <= 0 and tick % 20 == 0 then say((tick % 40 == 0) and "z" or "Z z", 12) end
    timer = timer - 1
    if timer <= 0 then state, timer = "walk", math.random(40, 160) end
  elseif state == "hop" then
    y = y - (timer > 3 and 6 or 3)
    set("Frame", "dog-walk1")
    timer = timer - 1
    if timer <= 0 then state, timer = "walk", math.random(40, 120) end
  end

  if said > 0 then
    said = said - 1
    if said == 0 then set("Say", "") end
  end

  SKIN:Bang("!Move", math.floor(x), math.floor(y))
  SKIN:Bang("!UpdateMeter", "*")
  SKIN:Bang("!Redraw")
  return 0
end
