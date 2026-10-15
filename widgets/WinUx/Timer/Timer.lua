-- WinUx Focus Timer: a pomodoro timer told as a battle.
-- focus: the TASK's HP drains to zero, then you win and take a break (your HP heals).

local phase = "focus"      -- "focus" or "break"
local running = false
local paused = false
local total, remain, ends = 0, 0, 0
local choice = 1

local function choices()
  local list = {}
  for n in string.gmatch(SKIN:GetVariable("Choices", "25,45,15"), "%d+") do list[#list + 1] = tonumber(n) end
  if #list == 0 then list = { 25 } end
  return list
end

local function sound(name)
  local file = SKIN:GetVariable("WinUxDir") .. "\\generated\\sounds\\" .. name .. ".wav"
  SKIN:Bang('[Play "' .. file .. '"]')
end

local function say(text)
  SKIN:Bang("!SetVariable", "Message", text)
end

local function show()
  local s = math.max(0, remain)
  SKIN:Bang("!SetVariable", "Clock", string.format("%02d:%02d", math.floor(s / 60), s % 60))
  SKIN:Bang("!UpdateMeter", "*")
  SKIN:Bang("!Redraw")
end

local function ready()
  phase, running, paused = "focus", false, false
  total = choices()[choice] * 60
  remain = total
  SKIN:Bang("!SetVariable", "Foe", "TASK")
  SKIN:Bang("!SetVariable", "BarColor", "0,255,0")
  SKIN:Bang("!SetVariable", "BarBack", "110,10,20")
end

function Initialize()
  ready()
  show()
end

function Fight()
  if running then
    say(phase == "focus" and "* You're already fighting! Keep FOCUSING." or "* Shh. You're resting.")
  else
    running, paused = true, false
    ends = os.time() + remain
    say(phase == "focus" and "* You attack the TASK! Stay focused..." or "* You take a break. HP is healing.")
    sound("blip")
  end
  show()
end

function Act()
  if running then
    say("* You can't ACT now! You're " .. (phase == "focus" and "FOCUSING." or "RESTING."))
  else
    local list = choices()
    choice = choice % #list + 1
    ready()
    say("* You check the TASK. It will take " .. list[choice] .. " minutes to defeat.")
  end
  show()
end

function Mercy()
  if running then
    running, paused = false, true
    remain = math.max(0, ends - os.time())
    say("* You paused. FIGHT to keep going, MERCY again to reset.")
  else
    ready()
    say("* You spared the TASK. Timer reset.")
  end
  show()
end

function Update()
  if running then
    remain = ends - os.time()
    if remain <= 0 then
      if phase == "focus" then
        local mins = math.floor(total / 60)
        phase = "break"
        total = tonumber(SKIN:GetVariable("BreakMinutes", "5")) * 60
        remain = total
        ends = os.time() + remain
        SKIN:Bang("!SetVariable", "Foe", "YOU")
        SKIN:Bang("!SetVariable", "BarColor", "255,230,0")
        SKIN:Bang("!SetVariable", "BarBack", "60,60,60")
        say("* YOU WON! Got " .. mins .. " EXP. Take a " .. math.floor(total / 60) .. " minute break.")
        sound("save")
      else
        ready()
        say("* You feel rested. The next TASK appears! Press FIGHT.")
        sound("alert")
      end
    end
    show()
  end
  if total <= 0 then return 0 end
  -- the bar: the TASK's HP drains while you focus; your HP fills up on a break
  if phase == "focus" then return remain / total end
  return 1 - remain / total
end
