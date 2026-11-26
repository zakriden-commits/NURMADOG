-- ============================================================
--  HelperSasny Plugin v1.0
--  Плагин-магазин веселья для Roblox Studio
--  Логотип: фиолетовый кубик (см. logo.png)
--  Кнопка "Установить в игру" сама ставит сервер + клиент + GUI
-- ============================================================

local ChangeHistoryService = game:GetService("ChangeHistoryService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ServerScriptService = game:GetService("ServerScriptService")
local StarterPlayer = game:GetService("StarterPlayer")

-- ============================================================
--  КОД СЕРВЕРА И КЛИЕНТА (встраивается в игру при установке)
-- ============================================================

local SERVER_CODE = [==[
-- HelperSasny Server v1.0
-- Серверная часть: обрабатывает все функции магазина HelperSasny
-- Устанавливается автоматически плагином HelperSasny

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local remotesFolder = ReplicatedStorage:WaitForChild("HelperSasnyRemotes")
local useFunctionEvent = remotesFolder:WaitForChild("UseFunction")

-- Кулдауны: [player] = { [funcName] = timestamp }
local cooldowns = {}
local COOLDOWN_TIME = 2 -- секунд между активациями одной функции

-- Активные эффекты: [player] = { [funcName] = thread/данные }
local activeEffects = {}

local function getCooldowns(player)
	if not cooldowns[player] then
		cooldowns[player] = {}
	end
	return cooldowns[player]
end

local function checkCooldown(player, funcName)
	local cd = getCooldowns(player)
	local now = os.clock()
	if cd[funcName] and (now - cd[funcName]) < COOLDOWN_TIME then
		return false
	end
	cd[funcName] = now
	return true
end

local function getCharacterParts(player)
	local character = player.Character
	if not character then return nil, nil, nil end
	local humanoid = character:FindFirstChildOfClass("Humanoid")
	local rootPart = character:FindFirstChild("HumanoidRootPart")
	if not humanoid or not rootPart then return nil, nil, nil end
	return character, humanoid, rootPart
end

-- ============================================================
-- ПОГОНЩИКИ: кубик / круг / треугольник
-- ============================================================
local function spawnChaser(player, shapeType)
	local character, humanoid, rootPart = getCharacterParts(player)
	if not character or not rootPart then return end

	-- Удалить старого погонщика этого игрока, если есть
	local prev = activeEffects[player] and activeEffects[player].Chaser
	if prev and prev.Parent then
		prev:Destroy()
	end

	local chaser = Instance.new("Part")
	chaser.Name = "HelperSasnyChaser_" .. shapeType
	chaser.Anchored = true
	chaser.CanCollide = false
	chaser.CanQuery = false
	chaser.CanTouch = true
	chaser.Material = Enum.Material.Neon

	if shapeType == "ChaseCube" then
		chaser.Shape = Enum.PartType.Block
		chaser.Size = Vector3.new(3, 3, 3)
		chaser.Color = Color3.fromRGB(255, 85, 85) -- красный кубик
	elseif shapeType == "ChaseCircle" then
		chaser.Shape = Enum.PartType.Cylinder
		chaser.Size = Vector3.new(1.2, 4.5, 4.5)
		chaser.Color = Color3.fromRGB(85, 170, 255) -- синий круг
	elseif shapeType == "ChaseTriangle" then
		-- Треугольник делаем WedgePart'ом
		chaser:Destroy()
		chaser = Instance.new("WedgePart")
		chaser.Name = "HelperSasnyChaser_" .. shapeType
		chaser.Anchored = true
		chaser.CanCollide = false
		chaser.CanQuery = false
		chaser.CanTouch = true
		chaser.Material = Enum.Material.Neon
		chaser.Size = Vector3.new(3.5, 3.5, 3.5)
		chaser.Color = Color3.fromRGB(255, 200, 50) -- жёлтый треугольник
	else
		return
	end

	-- Стартовая позиция: рядом с игроком
	local startPos = rootPart.Position + Vector3.new(0, 4, 0) + rootPart.CFrame.LookVector * -8
	chaser.CFrame = CFrame.new(startPos)
	chaser.Parent = workspace

	-- Свет
	local light = Instance.new("PointLight")
	light.Color = chaser.Color
	light.Brightness = 2
	light.Range = 16
	light.Parent = chaser

	-- Трейл
	local attachment = Instance.new("Attachment")
	attachment.Parent = chaser
	local trail = Instance.new("Trail")
	trail.Attachment0 = attachment
	trail.Lifetime = 0.35
	trail.MinLength = 0.1
	trail.Color = ColorSequence.new(chaser.Color)
	trail.Transparency = NumberSequence.new(0.2, 1)
	trail.Parent = chaser

	-- Частицы
	local emitter = Instance.new("ParticleEmitter")
	emitter.Rate = 25
	emitter.Lifetime = NumberRange.new(0.3, 0.6)
	emitter.Speed = NumberRange.new(1, 3)
	emitter.Size = NumberSequence.new(0.4)
	emitter.Color = ColorSequence.new(chaser.Color)
	emitter.Parent = chaser

	-- Глаза (две маленькие чёрные сферы спереди)
	local eyes = {}
	for _, offset in ipairs({Vector3.new(-0.8, 0.6, -1.55), Vector3.new(0.8, 0.6, -1.55)}) do
		local eye = Instance.new("Part")
		eye.Shape = Enum.PartType.Ball
		eye.Size = Vector3.new(0.5, 0.5, 0.5)
		eye.Color = Color3.fromRGB(20, 20, 20)
		eye.Material = Enum.Material.SmoothPlastic
		eye.Anchored = true
		eye.CanCollide = false
		eye.CanQuery = false
		eye.CFrame = chaser.CFrame * CFrame.new(offset)
		eye.Parent = chaser
		eye.Name = "Eye"
		table.insert(eyes, { part = eye, offset = offset })
	end

	if not activeEffects[player] then activeEffects[player] = {} end
	activeEffects[player].Chaser = chaser

	-- Отталкивание при касании
	local touchCooldown = 0
	chaser.Touched:Connect(function(hit)
		local now = os.clock()
		if now - touchCooldown < 0.5 then return end
		local hitChar = hit.Parent
		if hitChar and hitChar:FindFirstChildOfClass("Humanoid") then
			touchCooldown = now
			local targetRoot = hitChar:FindFirstChild("HumanoidRootPart")
			if targetRoot then
				local pushDir = (targetRoot.Position - chaser.Position).Unit
				targetRoot.AssemblyLinearVelocity = pushDir * 35 + Vector3.new(0, 25, 0)
			end
		end
	end)

	-- Цикл погони (12 секунд)
	task.spawn(function()
		local startTime = os.clock()
		local lifetime = 12
		while chaser.Parent and (os.clock() - startTime) < lifetime do
			local char, hum, targetRoot = getCharacterParts(player)
			if targetRoot and chaser.Parent then
				local targetPos = targetRoot.Position + Vector3.new(0, 1.5, 0)
				local currentPos = chaser.Position
				local direction = (targetPos - currentPos)
				local distance = direction.Magnitude
				if distance > 0.1 then
					local speed = 22 + (12 - (os.clock() - startTime)) * 0.3 -- ускоряется к концу
					local step = direction.Unit * math.min(speed * 0.016, distance)
					local newPos = currentPos + step
					-- Плавный поворот к игроку + вращение для стиля
					local lookCFrame = CFrame.lookAt(newPos, targetPos)
					local spin = CFrame.Angles(0, os.clock() * 4, 0)
					chaser.CFrame = lookCFrame * spin
					-- Обновить глаза (следуют за погонщиком)
					for _, eyeData in ipairs(eyes) do
						if eyeData.part.Parent then
							eyeData.part.CFrame = chaser.CFrame * CFrame.new(eyeData.offset)
						end
					end
				end
			end
			RunService.Heartbeat:Wait()
		end
		-- Взрыв при исчезновении
		if chaser.Parent then
			local explosion = Instance.new("ParticleEmitter")
			explosion.Rate = 0
			explosion.Speed = NumberRange.new(8, 15)
			explosion.Lifetime = NumberRange.new(0.4, 0.8)
			explosion.Size = NumberSequence.new(0.6)
			explosion.Color = ColorSequence.new(chaser.Color, Color3.fromRGB(255, 255, 255))
			explosion.Parent = chaser
			explosion:Emit(40)
			task.delay(0.6, function()
				if chaser.Parent then chaser:Destroy() end
			end)
		end
	end)
end

-- ============================================================
-- ВЫСОКИЙ ПРЫЖОК
-- ============================================================
local function activateHighJump(player)
	local character, humanoid, rootPart = getCharacterParts(player)
	if not humanoid then return end
	local oldJumpPower = humanoid.JumpPower
	local oldUseJumpPower = humanoid.UseJumpPower
	humanoid.UseJumpPower = true
	humanoid.JumpPower = 160
	task.delay(15, function()
		if humanoid.Parent then
			humanoid.JumpPower = oldJumpPower
			humanoid.UseJumpPower = oldUseJumpPower
		end
	end)
end

-- ============================================================
-- ЖИРНЫЙ НИК НАД ГОЛОВОЙ
-- ============================================================
local function toggleNickname(player)
	local character, humanoid, rootPart = getCharacterParts(player)
	if not character then return end
	local head = character:FindFirstChild("Head")
	if not head then return end

	local existing = head:FindFirstChild("HelperSasnyNick")
	if existing then
		existing:Destroy()
		return
	end

	local billboard = Instance.new("BillboardGui")
	billboard.Name = "HelperSasnyNick"
	billboard.Size = UDim2.new(0, 220, 0, 60)
	billboard.StudsOffset = Vector3.new(0, 2.2, 0)
	billboard.AlwaysOnTop = true
	billboard.LightInfluence = 0
	billboard.Parent = head

	local label = Instance.new("TextLabel")
	label.Size = UDim2.new(1, 0, 1, 0)
	label.BackgroundTransparency = 1
	label.Text = player.DisplayName
	label.Font = Enum.Font.GothamBlack -- жирный шрифт
	label.TextScaled = true
	label.TextColor3 = Color3.fromRGB(255, 255, 255)
	label.TextStrokeTransparency = 0.2
	label.TextStrokeColor3 = Color3.fromRGB(30, 20, 60)
	label.Parent = billboard

	local stroke = Instance.new("UIStroke")
	stroke.Thickness = 3
	stroke.Color = Color3.fromRGB(140, 100, 255)
	stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Contextual
	stroke.Parent = label

	local gradient = Instance.new("UIGradient")
	gradient.Color = ColorSequence.new({
		ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 255, 255)),
		ColorSequenceKeypoint.new(0.5, Color3.fromRGB(200, 170, 255)),
		ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 255, 255)),
	})
	gradient.Parent = label

	-- Лёгкая пульсация
	task.spawn(function()
		while billboard.Parent do
			local tween = TweenService:Create(label, TweenInfo.new(0.6, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut), {
				TextColor3 = Color3.fromRGB(255, 230, 150),
			})
			tween:Play()
			tween.Completed:Wait()
			local tween2 = TweenService:Create(label, TweenInfo.new(0.6, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut), {
				TextColor3 = Color3.fromRGB(255, 255, 255),
			})
			tween2:Play()
			tween2.Completed:Wait()
		end
	end)
end

-- ============================================================
-- RAGDOLL
-- ============================================================
local ragdollData = {} -- [player] = { sockets = {}, motors = {} }

local function setRagdoll(player, enabled)
	local character, humanoid, rootPart = getCharacterParts(player)
	if not character or not humanoid then return end

	if enabled then
		if ragdollData[player] then return end -- уже в ragdoll
		local data = { sockets = {}, attachments = {}, motors = {} }
		humanoid:ChangeState(Enum.HumanoidState.Physics)
		for _, descendant in ipairs(character:GetDescendants()) do
			if descendant:IsA("Motor6D") and descendant.Part0 and descendant.Part1 then
				descendant.Enabled = false
				table.insert(data.motors, descendant)

				local att0 = Instance.new("Attachment")
				att0.Position = descendant.C0.Position
				att0.Parent = descendant.Part0

				local att1 = Instance.new("Attachment")
				att1.Position = descendant.C0.Position
				att1.Parent = descendant.Part1

				local socket = Instance.new("BallSocketConstraint")
				socket.Attachment0 = att0
				socket.Attachment1 = att1
				socket.LimitsEnabled = true
				socket.MaxFrictionTorque = 0
				socket.Parent = character

				table.insert(data.sockets, socket)
				table.insert(data.attachments, att0)
				table.insert(data.attachments, att1)
			end
		end
		ragdollData[player] = data
		-- Автовосстановление через 3.5 сек
		task.delay(3.5, function()
			if ragdollData[player] then
				setRagdoll(player, false)
			end
		end)
	else
		local data = ragdollData[player]
		if not data then return end
		for _, socket in ipairs(data.sockets) do
			if socket.Parent then socket:Destroy() end
		end
		for _, att in ipairs(data.attachments) do
			if att.Parent then att:Destroy() end
		end
		for _, motor in ipairs(data.motors) do
			if motor.Parent then motor.Enabled = true end
		end
		ragdollData[player] = nil
		if humanoid.Parent then
			humanoid:ChangeState(Enum.HumanoidState.GettingUp)
		end
	end
end

local function toggleRagdoll(player)
	if ragdollData[player] then
		setRagdoll(player, false)
	else
		setRagdoll(player, true)
	end
end

-- ============================================================
-- БОНУС: СКОРОСТЬ x2
-- ============================================================
local function activateSpeedBoost(player)
	local character, humanoid, rootPart = getCharacterParts(player)
	if not humanoid then return end
	local oldSpeed = humanoid.WalkSpeed
	humanoid.WalkSpeed = 32
	task.delay(10, function()
		if humanoid.Parent then
			humanoid.WalkSpeed = oldSpeed
		end
	end)
end

-- ============================================================
-- БОНУС: РАДУЖНАЯ АУРА
-- ============================================================
local function activateRainbowAura(player)
	local character, humanoid, rootPart = getCharacterParts(player)
	if not rootPart then return end

	local existing = rootPart:FindFirstChild("HelperSasnyAura")
	if existing then existing:Destroy() end

	local attachment = Instance.new("Attachment")
	attachment.Name = "HelperSasnyAura"
	attachment.Parent = rootPart

	local emitter = Instance.new("ParticleEmitter")
	emitter.Rate = 40
	emitter.Lifetime = NumberRange.new(0.6, 1.1)
	emitter.Speed = NumberRange.new(1, 2.5)
	emitter.SpreadAngle = Vector2.new(180, 180)
	emitter.Size = NumberSequence.new(0.5)
	emitter.Parent = attachment

	local light = Instance.new("PointLight")
	light.Brightness = 1.5
	light.Range = 12
	light.Parent = rootPart

	local colors = {
		Color3.fromRGB(255, 85, 85),
		Color3.fromRGB(255, 170, 0),
		Color3.fromRGB(255, 255, 85),
		Color3.fromRGB(85, 255, 85),
		Color3.fromRGB(85, 170, 255),
		Color3.fromRGB(170, 85, 255),
		Color3.fromRGB(255, 85, 200),
	}
	local index = 1
	task.spawn(function()
		local start = os.clock()
		while attachment.Parent and (os.clock() - start) < 12 do
			local color = colors[index]
			emitter.Color = ColorSequence.new(color)
			light.Color = color
			index = index % #colors + 1
			task.wait(0.12)
		end
		if attachment.Parent then attachment:Destroy() end
		if light.Parent then light:Destroy() end
	end)
end

-- ============================================================
-- БОНУС: КОНФЕТТИ-ВЕЧЕРИНКА
-- ============================================================
local function activateConfetti(player)
	local character, humanoid, rootPart = getCharacterParts(player)
	if not rootPart then return end

	local brightColors = {
		Color3.fromRGB(255, 85, 85),
		Color3.fromRGB(255, 170, 0),
		Color3.fromRGB(85, 255, 85),
		Color3.fromRGB(85, 170, 255),
		Color3.fromRGB(170, 85, 255),
		Color3.fromRGB(255, 85, 200),
		Color3.fromRGB(255, 255, 85),
	}

	for i = 1, 60 do
		local confetti = Instance.new("Part")
		confetti.Shape = Enum.PartType.Block
		confetti.Size = Vector3.new(0.8, 0.15, 0.8)
		confetti.Color = brightColors[math.random(1, #brightColors)]
		confetti.Material = Enum.Material.Neon
		confetti.CanCollide = false
		confetti.CFrame = rootPart.CFrame * CFrame.new(
			math.random(-3, 3),
			math.random(2, 5),
			math.random(-3, 3)
		)
		confetti.Parent = workspace
		confetti.AssemblyLinearVelocity = Vector3.new(
			math.random(-8, 8),
			math.random(10, 20),
			math.random(-8, 8)
		)
		confetti.AssemblyAngularVelocity = Vector3.new(
			math.random(-10, 10),
			math.random(-10, 10),
			math.random(-10, 10)
		)
		task.delay(3, function()
			if confetti.Parent then confetti:Destroy() end
		end)
	end

	-- Вспышка частиц
	local burst = Instance.new("ParticleEmitter")
	burst.Rate = 0
	burst.Speed = NumberRange.new(10, 18)
	burst.Lifetime = NumberRange.new(0.5, 1)
	burst.Size = NumberSequence.new(0.5)
	burst.Color = ColorSequence.new(brightColors[math.random(1, #brightColors)])
	burst.Parent = rootPart
	burst:Emit(50)
	task.delay(1.2, function()
		if burst.Parent then burst:Destroy() end
	end)
end

-- ============================================================
-- БОНУС: ГИГАНТ
-- ============================================================
local function activateGiant(player)
	local character, humanoid, rootPart = getCharacterParts(player)
	if not character then return end
	local ok, _ = pcall(function()
		character:ScaleTo(1.7)
	end)
	if not ok then
		-- Fallback для старых версий: увеличиваем HumanoidRootPart
		if rootPart then
			rootPart.Size = rootPart.Size * 1.5
		end
	end
	task.delay(12, function()
		if character.Parent then
			pcall(function()
				character:ScaleTo(1)
			end)
		end
	end)
end

-- ============================================================
-- ОБРАБОТЧИК КОМАНД
-- ============================================================
local function handleFunction(player, funcName)
	if not checkCooldown(player, funcName) then return end

	if funcName == "ChaseCube" or funcName == "ChaseCircle" or funcName == "ChaseTriangle" then
		spawnChaser(player, funcName)
	elseif funcName == "HighJump" then
		activateHighJump(player)
	elseif funcName == "Nickname" then
		toggleNickname(player)
	elseif funcName == "Ragdoll" then
		toggleRagdoll(player)
	elseif funcName == "SpeedBoost" then
		activateSpeedBoost(player)
	elseif funcName == "RainbowAura" then
		activateRainbowAura(player)
	elseif funcName == "Confetti" then
		activateConfetti(player)
	elseif funcName == "Giant" then
		activateGiant(player)
	end
end

useFunctionEvent.OnServerEvent:Connect(handleFunction)

Players.PlayerRemoving:Connect(function(player)
	cooldowns[player] = nil
	if activeEffects[player] and activeEffects[player].Chaser then
		local chaser = activeEffects[player].Chaser
		if chaser.Parent then chaser:Destroy() end
	end
	activeEffects[player] = nil
	ragdollData[player] = nil
end)

print("[HelperSasny] Сервер загружен! Функций: 10")
]==]

local CLIENT_CODE = [==[
-- HelperSasny Client v1.0
-- Клиентская часть: магазин-меню HelperSasny в игре
-- Устанавливается автоматически плагином HelperSasny

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local TweenService = game:GetService("TweenService")

local player = Players.LocalPlayer
local playerGui = player:WaitForChild("PlayerGui")

local remotesFolder = ReplicatedStorage:WaitForChild("HelperSasnyRemotes")
local useFunctionEvent = remotesFolder:WaitForChild("UseFunction")

-- Цвета в стиле логотипа (фиолетовый + мятный)
local COLORS = {
	Background = Color3.fromRGB(28, 26, 42),
	BackgroundLight = Color3.fromRGB(42, 38, 62),
	Accent = Color3.fromRGB(160, 130, 255),
	AccentMint = Color3.fromRGB(140, 230, 200),
	Text = Color3.fromRGB(255, 255, 255),
	TextDim = Color3.fromRGB(180, 175, 200),
	Stroke = Color3.fromRGB(90, 80, 140),
}

-- Данные магазина
local SHOP_ITEMS = {
	{ id = "ChaseCube", emoji = "🟥", name = "Кубик-погонщик", desc = "Кубик гонится за тобой!", color = Color3.fromRGB(255, 85, 85) },
	{ id = "ChaseCircle", emoji = "🔵", name = "Круг-погонщик", desc = "Синий круг не отстаёт", color = Color3.fromRGB(85, 170, 255) },
	{ id = "ChaseTriangle", emoji = "🔺", name = "Треугольник", desc = "Жёлтый треугольник летит!", color = Color3.fromRGB(255, 200, 50) },
	{ id = "HighJump", emoji = "🚀", name = "Высокий прыжок", desc = "Прыгай до небес", color = Color3.fromRGB(85, 255, 170) },
	{ id = "Nickname", emoji = "👑", name = "Жирный ник", desc = "Ник над головой", color = Color3.fromRGB(255, 170, 85) },
	{ id = "Ragdoll", emoji = "🤕", name = "Ragdoll [R]", desc = "Нажми R — упадёшь!", color = Color3.fromRGB(255, 120, 200) },
	{ id = "SpeedBoost", emoji = "⚡", name = "Скорость x2", desc = "Бегай быстрее", color = Color3.fromRGB(255, 255, 85) },
	{ id = "RainbowAura", emoji = "🌈", name = "Радужная аура", desc = "Светись как радуга", color = Color3.fromRGB(170, 85, 255) },
	{ id = "Confetti", emoji = "🎉", name = "Конфетти", desc = "Вечеринка!", color = Color3.fromRGB(85, 255, 200) },
	{ id = "Giant", emoji = "🐾", name = "Гигант", desc = "Стань огромным", color = Color3.fromRGB(255, 150, 100) },
}

-- Удалить старый GUI при перезапуске
local oldGui = playerGui:FindFirstChild("HelperSasnyShop")
if oldGui then oldGui:Destroy() end

local screenGui = Instance.new("ScreenGui")
screenGui.Name = "HelperSasnyShop"
screenGui.ResetOnSpawn = false
screenGui.IgnoreGuiInset = true
screenGui.DisplayOrder = 10
screenGui.Parent = playerGui

-- ============================================================
-- ПЛАВАЮЩАЯ КНОПКА HS
-- ============================================================
local toggleButton = Instance.new("TextButton")
toggleButton.Name = "ToggleButton"
toggleButton.Size = UDim2.new(0, 64, 0, 64)
toggleButton.Position = UDim2.new(1, -84, 1, -84)
toggleButton.AnchorPoint = Vector2.new(0, 0)
toggleButton.BackgroundColor3 = COLORS.Accent
toggleButton.Text = "HS"
toggleButton.Font = Enum.Font.GothamBlack
toggleButton.TextSize = 24
toggleButton.TextColor3 = Color3.fromRGB(255, 255, 255)
toggleButton.AutoButtonColor = false
toggleButton.Parent = screenGui

local toggleCorner = Instance.new("UICorner")
toggleCorner.CornerRadius = UDim.new(0, 20)
toggleCorner.Parent = toggleButton

local toggleStroke = Instance.new("UIStroke")
toggleStroke.Thickness = 3
toggleStroke.Color = COLORS.AccentMint
toggleStroke.Parent = toggleButton

local toggleGradient = Instance.new("UIGradient")
toggleGradient.Color = ColorSequence.new(COLORS.Accent, COLORS.AccentMint)
toggleGradient.Rotation = 45
toggleGradient.Parent = toggleButton

-- ============================================================
-- ГЛАВНАЯ ПАНЕЛЬ МАГАЗИНА
-- ============================================================
local mainFrame = Instance.new("Frame")
mainFrame.Name = "MainFrame"
mainFrame.Size = UDim2.new(0, 360, 0, 500)
mainFrame.Position = UDim2.new(0.5, 0, 0.5, 0)
mainFrame.AnchorPoint = Vector2.new(0.5, 0.5)
mainFrame.BackgroundColor3 = COLORS.Background
mainFrame.BorderSizePixel = 0
mainFrame.Visible = false
mainFrame.Parent = screenGui

local mainCorner = Instance.new("UICorner")
mainCorner.CornerRadius = UDim.new(0, 22)
mainCorner.Parent = mainFrame

local mainStroke = Instance.new("UIStroke")
mainStroke.Thickness = 2
mainStroke.Color = COLORS.Stroke
mainStroke.Parent = mainFrame

local mainGradient = Instance.new("UIGradient")
mainGradient.Color = ColorSequence.new({
	ColorSequenceKeypoint.new(0, COLORS.Background),
	ColorSequenceKeypoint.new(1, COLORS.BackgroundLight),
})
mainGradient.Rotation = 90
mainGradient.Parent = mainFrame

-- Шапка с логотипом
local header = Instance.new("Frame")
header.Name = "Header"
header.Size = UDim2.new(1, 0, 0, 84)
header.BackgroundColor3 = COLORS.BackgroundLight
header.BorderSizePixel = 0
header.Parent = mainFrame

local headerCorner = Instance.new("UICorner")
headerCorner.CornerRadius = UDim.new(0, 22)
headerCorner.Parent = header

-- Логотип-кружок
local logoCircle = Instance.new("Frame")
logoCircle.Name = "Logo"
logoCircle.Size = UDim2.new(0, 56, 0, 56)
logoCircle.Position = UDim2.new(0, 14, 0.5, 0)
logoCircle.AnchorPoint = Vector2.new(0, 0.5)
logoCircle.BackgroundColor3 = COLORS.Accent
logoCircle.BorderSizePixel = 0
logoCircle.Parent = header

local logoCorner = Instance.new("UICorner")
logoCorner.CornerRadius = UDim.new(0, 18)
logoCorner.Parent = logoCircle

local logoGradient = Instance.new("UIGradient")
logoGradient.Color = ColorSequence.new(COLORS.Accent, COLORS.AccentMint)
logoGradient.Rotation = 45
logoGradient.Parent = logoCircle

local logoText = Instance.new("TextLabel")
logoText.Size = UDim2.new(1, 0, 1, 0)
logoText.BackgroundTransparency = 1
logoText.Text = "🟪"
logoText.Font = Enum.Font.GothamBlack
logoText.TextSize = 30
logoText.Parent = logoCircle

local titleLabel = Instance.new("TextLabel")
titleLabel.Name = "Title"
titleLabel.Size = UDim2.new(0, 200, 0, 30)
titleLabel.Position = UDim2.new(0, 82, 0, 12)
titleLabel.BackgroundTransparency = 1
titleLabel.Text = "HelperSasny"
titleLabel.Font = Enum.Font.GothamBlack
titleLabel.TextSize = 24
titleLabel.TextColor3 = COLORS.Text
titleLabel.TextXAlignment = Enum.TextXAlignment.Left
titleLabel.Parent = header

local subtitleLabel = Instance.new("TextLabel")
subtitleLabel.Name = "Subtitle"
subtitleLabel.Size = UDim2.new(0, 200, 0, 20)
subtitleLabel.Position = UDim2.new(0, 82, 0, 44)
subtitleLabel.BackgroundTransparency = 1
subtitleLabel.Text = "Магазин веселья ✨"
subtitleLabel.Font = Enum.Font.Gotham
subtitleLabel.TextSize = 13
subtitleLabel.TextColor3 = COLORS.TextDim
subtitleLabel.TextXAlignment = Enum.TextXAlignment.Left
subtitleLabel.Parent = header

local closeButton = Instance.new("TextButton")
closeButton.Name = "CloseButton"
closeButton.Size = UDim2.new(0, 36, 0, 36)
closeButton.Position = UDim2.new(1, -48, 0, 12)
closeButton.BackgroundColor3 = Color3.fromRGB(60, 55, 85)
closeButton.Text = "✕"
closeButton.Font = Enum.Font.GothamBlack
closeButton.TextSize = 16
closeButton.TextColor3 = COLORS.Text
closeButton.Parent = header

local closeCorner = Instance.new("UICorner")
closeCorner.CornerRadius = UDim.new(0, 12)
closeCorner.Parent = closeButton

-- Скролл-лист товаров
local scrollFrame = Instance.new("ScrollingFrame")
scrollFrame.Name = "ShopList"
scrollFrame.Size = UDim2.new(1, -20, 1, -150)
scrollFrame.Position = UDim2.new(0, 10, 0, 94)
scrollFrame.BackgroundTransparency = 1
scrollFrame.BorderSizePixel = 0
scrollFrame.ScrollBarThickness = 4
scrollFrame.ScrollBarImageColor3 = COLORS.Accent
scrollFrame.CanvasSize = UDim2.new(0, 0, 0, 0)
scrollFrame.AutomaticCanvasSize = Enum.AutomaticSize.Y
scrollFrame.Parent = mainFrame

local gridLayout = Instance.new("UIGridLayout")
gridLayout.CellSize = UDim2.new(0, 160, 0, 92)
gridLayout.CellPadding = UDim2.new(0, 10, 0, 10)
gridLayout.SortOrder = Enum.SortOrder.LayoutOrder
gridLayout.Parent = scrollFrame

local padding = Instance.new("UIPadding")
padding.PaddingTop = UDim.new(0, 4)
padding.PaddingLeft = UDim.new(0, 4)
padding.PaddingRight = UDim.new(0, 4)
padding.Parent = scrollFrame

-- Подвал с подсказкой
local footer = Instance.new("TextLabel")
footer.Name = "Footer"
footer.Size = UDim2.new(1, -20, 0, 36)
footer.Position = UDim2.new(0, 10, 1, -46)
footer.BackgroundTransparency = 1
footer.Text = "R — Ragdoll • HS — свернуть магазин"
footer.Font = Enum.Font.Gotham
footer.TextSize = 12
footer.TextColor3 = COLORS.TextDim
footer.Parent = mainFrame

-- Тост-уведомление
local toast = Instance.new("TextLabel")
toast.Name = "Toast"
toast.Size = UDim2.new(0, 280, 0, 44)
toast.Position = UDim2.new(0.5, 0, 1, -110)
toast.AnchorPoint = Vector2.new(0.5, 0)
toast.BackgroundColor3 = COLORS.BackgroundLight
toast.Text = ""
toast.Font = Enum.Font.GothamBold
toast.TextSize = 15
toast.TextColor3 = COLORS.Text
toast.Visible = false
toast.Parent = screenGui

local toastCorner = Instance.new("UICorner")
toastCorner.CornerRadius = UDim.new(0, 14)
toastCorner.Parent = toast

local toastStroke = Instance.new("UIStroke")
toastStroke.Thickness = 1
toastStroke.Color = COLORS.Accent
toastStroke.Parent = toast

local toastTween
local function showToast(text)
	toast.Text = text
	toast.Visible = true
	toast.BackgroundTransparency = 0
	if toastTween then toastTween:Cancel() end
	toastTween = TweenService:Create(toast, TweenInfo.new(0.3), { BackgroundTransparency = 0 })
	toastTween:Play()
	task.delay(1.8, function()
		local fade = TweenService:Create(toast, TweenInfo.new(0.4), { BackgroundTransparency = 1 })
		fade:Play()
		fade.Completed:Wait()
		toast.Visible = false
	end)
end

-- Создание кнопок товаров
for index, item in ipairs(SHOP_ITEMS) do
	local button = Instance.new("TextButton")
	button.Name = item.id
	button.LayoutOrder = index
	button.BackgroundColor3 = COLORS.BackgroundLight
	button.Text = ""
	button.AutoButtonColor = false
	button.Parent = scrollFrame

	local btnCorner = Instance.new("UICorner")
	btnCorner.CornerRadius = UDim.new(0, 16)
	btnCorner.Parent = button

	local btnStroke = Instance.new("UIStroke")
	btnStroke.Thickness = 1
	btnStroke.Color = item.color
	btnStroke.Transparency = 0.4
	btnStroke.Parent = button

	local emojiLabel = Instance.new("TextLabel")
	emojiLabel.Size = UDim2.new(0, 40, 0, 40)
	emojiLabel.Position = UDim2.new(0, 8, 0, 6)
	emojiLabel.BackgroundTransparency = 1
	emojiLabel.Text = item.emoji
	emojiLabel.Font = Enum.Font.GothamBlack
	emojiLabel.TextSize = 28
	emojiLabel.Parent = button

	local nameLabel = Instance.new("TextLabel")
	nameLabel.Size = UDim2.new(1, -56, 0, 22)
	nameLabel.Position = UDim2.new(0, 52, 0, 8)
	nameLabel.BackgroundTransparency = 1
	nameLabel.Text = item.name
	nameLabel.Font = Enum.Font.GothamBlack
	nameLabel.TextSize = 14
	nameLabel.TextColor3 = COLORS.Text
	nameLabel.TextXAlignment = Enum.TextXAlignment.Left
	nameLabel.Parent = button

	local descLabel = Instance.new("TextLabel")
	descLabel.Size = UDim2.new(1, -16, 0, 30)
	descLabel.Position = UDim2.new(0, 8, 0, 52)
	descLabel.BackgroundTransparency = 1
	descLabel.Text = item.desc
	descLabel.Font = Enum.Font.Gotham
	descLabel.TextSize = 11
	descLabel.TextColor3 = COLORS.TextDim
	descLabel.TextXAlignment = Enum.TextXAlignment.Left
	descLabel.TextWrapped = true
	descLabel.Parent = button

	-- Hover-эффект
	button.MouseEnter:Connect(function()
		TweenService:Create(btnStroke, TweenInfo.new(0.15), { Transparency = 0 }):Play()
		TweenService:Create(button, TweenInfo.new(0.15), { BackgroundColor3 = Color3.fromRGB(55, 50, 80) }):Play()
	end)
	button.MouseLeave:Connect(function()
		TweenService:Create(btnStroke, TweenInfo.new(0.15), { Transparency = 0.4 }):Play()
		TweenService:Create(button, TweenInfo.new(0.15), { BackgroundColor3 = COLORS.BackgroundLight }):Play()
	end)

	button.MouseButton1Click:Connect(function()
		useFunctionEvent:FireServer(item.id)
		showToast(item.emoji .. " " .. item.name .. " — активировано!")
		-- Анимация нажатия
		local clickTween = TweenService:Create(button, TweenInfo.new(0.1, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, 1, true), {
			Size = UDim2.new(0, 152, 0, 86),
		})
		clickTween:Play()
	end)
end

-- Открытие / закрытие магазина
local isOpen = false
local function openShop()
	isOpen = true
	mainFrame.Visible = true
	mainFrame.Size = UDim2.new(0, 300, 0, 420)
	mainFrame.BackgroundTransparency = 1
	local tween = TweenService:Create(mainFrame, TweenInfo.new(0.3, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {
		Size = UDim2.new(0, 360, 0, 500),
		BackgroundTransparency = 0,
	})
	tween:Play()
end

local function closeShop()
	isOpen = false
	local tween = TweenService:Create(mainFrame, TweenInfo.new(0.2), {
		Size = UDim2.new(0, 300, 0, 420),
		BackgroundTransparency = 1,
	})
	tween:Play()
	tween.Completed:Wait()
	mainFrame.Visible = false
end

toggleButton.MouseButton1Click:Connect(function()
	if isOpen then
		closeShop()
	else
		openShop()
	end
end)

closeButton.MouseButton1Click:Connect(closeShop)

-- Клавиша R — Ragdoll
UserInputService.InputBegan:Connect(function(input, gameProcessed)
	if gameProcessed then return end
	if input.KeyCode == Enum.KeyCode.R then
		useFunctionEvent:FireServer("Ragdoll")
		showToast("🤕 Ragdoll!")
	end
end)

-- Приветствие
task.delay(1, function()
	showToast("🟪 HelperSasny загружен! Нажми HS")
end)

print("[HelperSasny] Клиент загружен! Магазин готов")
]==]

-- ============================================================
--  СОЗДАНИЕ ПАНЕЛИ ПЛАГИНА
-- ============================================================

local toolbar = plugin:CreateToolbar("HelperSasny")
-- Иконка кнопки: замени 0 на ID своего логотипа после загрузки logo.png в Roblox
-- Как загрузить: Creator Dashboard -> Creations -> Images -> Upload logo.png -> скопируй ID
local ICON_ID = "rbxassetid://0"
local button = toolbar:CreateButton("HelperSasny", "Открыть HelperSasny", ICON_ID)
button.ClickableWhenViewportHidden = true

local widgetInfo = DockWidgetPluginGuiInfo.new(
	Enum.InitialDockState.Float,
	false, -- не включён по умолчанию
	false, -- не скрыт
	360, 560, -- размер по умолчанию
	300, 420 -- минимальный размер
)

local widget = plugin:CreateDockWidgetPluginGui("HelperSasnyWidget", widgetInfo)
widget.Title = "HelperSasny"
widget.ZIndexBehavior = Enum.ZIndexBehavior.Sibling

local COLORS = {
	Background = Color3.fromRGB(28, 26, 42),
	BackgroundLight = Color3.fromRGB(42, 38, 62),
	Accent = Color3.fromRGB(160, 130, 255),
	AccentMint = Color3.fromRGB(140, 230, 200),
	Text = Color3.fromRGB(255, 255, 255),
	TextDim = Color3.fromRGB(180, 175, 200),
	Stroke = Color3.fromRGB(90, 80, 140),
	Green = Color3.fromRGB(85, 255, 170),
	Red = Color3.fromRGB(255, 100, 100),
}

local function createCorner(parent, radius)
	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, radius or 12)
	corner.Parent = parent
	return corner
end

local function createStroke(parent, color, thickness)
	local stroke = Instance.new("UIStroke")
	stroke.Color = color or COLORS.Stroke
	stroke.Thickness = thickness or 1
	stroke.Parent = parent
	return stroke
end

-- Фон виджета
local background = Instance.new("Frame")
background.Size = UDim2.new(1, 0, 1, 0)
background.BackgroundColor3 = COLORS.Background
background.BorderSizePixel = 0
background.Parent = widget

local bgGradient = Instance.new("UIGradient")
bgGradient.Color = ColorSequence.new(COLORS.Background, COLORS.BackgroundLight)
bgGradient.Rotation = 90
bgGradient.Parent = background

-- Скролл-контейнер
local scroll = Instance.new("ScrollingFrame")
scroll.Size = UDim2.new(1, -16, 1, -16)
scroll.Position = UDim2.new(0, 8, 0, 8)
scroll.BackgroundTransparency = 1
scroll.BorderSizePixel = 0
scroll.ScrollBarThickness = 4
scroll.ScrollBarImageColor3 = COLORS.Accent
scroll.CanvasSize = UDim2.new(0, 0, 0, 0)
scroll.AutomaticCanvasSize = Enum.AutomaticSize.Y
scroll.Parent = background

local layout = Instance.new("UIListLayout")
layout.Padding = UDim.new(0, 10)
layout.SortOrder = Enum.SortOrder.LayoutOrder
layout.HorizontalAlignment = Enum.HorizontalAlignment.Center
layout.Parent = scroll

local padding = Instance.new("UIPadding")
padding.PaddingTop = UDim.new(0, 8)
padding.PaddingBottom = UDim.new(0, 8)
padding.PaddingLeft = UDim.new(0, 8)
padding.PaddingRight = UDim.new(0, 8)
padding.Parent = scroll

-- Шапка с логотипом
local header = Instance.new("Frame")
header.Size = UDim2.new(1, 0, 0, 90)
header.BackgroundColor3 = COLORS.BackgroundLight
header.BorderSizePixel = 0
header.LayoutOrder = 1
header.Parent = scroll
createCorner(header, 18)
createStroke(header)

local logoCircle = Instance.new("Frame")
logoCircle.Size = UDim2.new(0, 60, 0, 60)
logoCircle.Position = UDim2.new(0, 14, 0.5, 0)
logoCircle.AnchorPoint = Vector2.new(0, 0.5)
logoCircle.BackgroundColor3 = COLORS.Accent
logoCircle.BorderSizePixel = 0
logoCircle.Parent = header
createCorner(logoCircle, 20)

local logoGradient = Instance.new("UIGradient")
logoGradient.Color = ColorSequence.new(COLORS.Accent, COLORS.AccentMint)
logoGradient.Rotation = 45
logoGradient.Parent = logoCircle

local logoText = Instance.new("TextLabel")
logoText.Size = UDim2.new(1, 0, 1, 0)
logoText.BackgroundTransparency = 1
logoText.Text = "🟪"
logoText.Font = Enum.Font.GothamBlack
logoText.TextSize = 32
logoText.Parent = logoCircle

local titleLabel = Instance.new("TextLabel")
titleLabel.Size = UDim2.new(1, -90, 0, 30)
titleLabel.Position = UDim2.new(0, 86, 0, 14)
titleLabel.BackgroundTransparency = 1
titleLabel.Text = "HelperSasny"
titleLabel.Font = Enum.Font.GothamBlack
titleLabel.TextSize = 24
titleLabel.TextColor3 = COLORS.Text
titleLabel.TextXAlignment = Enum.TextXAlignment.Left
titleLabel.Parent = header

local subtitleLabel = Instance.new("TextLabel")
subtitleLabel.Size = UDim2.new(1, -90, 0, 20)
subtitleLabel.Position = UDim2.new(0, 86, 0, 46)
subtitleLabel.BackgroundTransparency = 1
subtitleLabel.Text = "Магазин веселья для твоей игры ✨"
subtitleLabel.Font = Enum.Font.Gotham
subtitleLabel.TextSize = 12
subtitleLabel.TextColor3 = COLORS.TextDim
subtitleLabel.TextXAlignment = Enum.TextXAlignment.Left
subtitleLabel.Parent = header

-- Статус
local statusLabel = Instance.new("TextLabel")
statusLabel.Size = UDim2.new(1, 0, 0, 28)
statusLabel.BackgroundColor3 = COLORS.BackgroundLight
statusLabel.Text = "● Не установлен"
statusLabel.Font = Enum.Font.GothamBold
statusLabel.TextSize = 13
statusLabel.TextColor3 = COLORS.TextDim
statusLabel.LayoutOrder = 2
statusLabel.Parent = scroll
createCorner(statusLabel, 10)
createStroke(statusLabel)

-- Кнопка Установить
local installButton = Instance.new("TextButton")
installButton.Size = UDim2.new(1, 0, 0, 52)
installButton.BackgroundColor3 = COLORS.Accent
installButton.Text = "🚀  Установить в игру"
installButton.Font = Enum.Font.GothamBlack
installButton.TextSize = 16
installButton.TextColor3 = Color3.fromRGB(255, 255, 255)
installButton.AutoButtonColor = false
installButton.LayoutOrder = 3
installButton.Parent = scroll
createCorner(installButton, 14)

local installGradient = Instance.new("UIGradient")
installGradient.Color = ColorSequence.new(COLORS.Accent, COLORS.AccentMint)
installGradient.Rotation = 45
installGradient.Parent = installButton

-- Кнопка Удалить
local removeButton = Instance.new("TextButton")
removeButton.Size = UDim2.new(1, 0, 0, 44)
removeButton.BackgroundColor3 = Color3.fromRGB(60, 50, 70)
removeButton.Text = "🗑  Удалить из игры"
removeButton.Font = Enum.Font.GothamBold
removeButton.TextSize = 14
removeButton.TextColor3 = COLORS.Text
removeButton.AutoButtonColor = false
removeButton.LayoutOrder = 4
removeButton.Parent = scroll
createCorner(removeButton, 12)
createStroke(removeButton, COLORS.Red)

-- Заголовок списка функций
local listTitle = Instance.new("TextLabel")
listTitle.Size = UDim2.new(1, 0, 0, 24)
listTitle.BackgroundTransparency = 1
listTitle.Text = "Что внутри магазина (10 функций):"
listTitle.Font = Enum.Font.GothamBlack
listTitle.TextSize = 14
listTitle.TextColor3 = COLORS.Text
listTitle.TextXAlignment = Enum.TextXAlignment.Left
listTitle.LayoutOrder = 5
listTitle.Parent = scroll

local FUNCTIONS_LIST = {
	"🟥 Кубик-погонщик — гонится и толкает",
	"🔵 Круг-погонщик — синий и быстрый",
	"🔺 Треугольник — жёлтый, с трейлом",
	"🚀 Высокий прыжок — JumpPower 160",
	"👑 Жирный ник — GothamBlack над головой",
	"🤕 Ragdoll на R — реалистичное падение",
	"⚡ Скорость x2 — WalkSpeed 32",
	"🌈 Радужная аура — частицы + свет",
	"🎉 Конфетти — 60 неоновых кусочков",
	"🐾 Гигант — ScaleTo 1.7",
}

for i, text in ipairs(FUNCTIONS_LIST) do
	local item = Instance.new("TextLabel")
	item.Size = UDim2.new(1, 0, 0, 26)
	item.BackgroundColor3 = COLORS.BackgroundLight
	item.Text = "  " .. text
	item.Font = Enum.Font.Gotham
	item.TextSize = 13
	item.TextColor3 = COLORS.Text
	item.TextXAlignment = Enum.TextXAlignment.Left
	item.LayoutOrder = 5 + i
	item.Parent = scroll
	createCorner(item, 8)
end

local hintLabel = Instance.new("TextLabel")
hintLabel.Size = UDim2.new(1, 0, 0, 60)
hintLabel.BackgroundTransparency = 1
hintLabel.Text = "Нажми «Установить в игру» — плагин сам создаст сервер, клиент и магазин. В игре нажми кнопку HS справа внизу."
hintLabel.Font = Enum.Font.Gotham
hintLabel.TextSize = 12
hintLabel.TextColor3 = COLORS.TextDim
hintLabel.TextWrapped = true
hintLabel.LayoutOrder = 20
hintLabel.Parent = scroll

-- ============================================================
--  ЛОГИКА УСТАНОВКИ
-- ============================================================

local function isInstalled()
	local serverExists = ServerScriptService:FindFirstChild("HelperSasnyServer") ~= nil
	local clientExists = StarterPlayer:FindFirstChildOfClass("StarterPlayerScripts") and StarterPlayer.StarterPlayerScripts:FindFirstChild("HelperSasnyClient") ~= nil
	return serverExists and clientExists
end

local function refreshStatus()
	if isInstalled() then
		statusLabel.Text = "● Установлен — магазин работает в игре!"
		statusLabel.TextColor3 = COLORS.Green
	else
		statusLabel.Text = "● Не установлен"
		statusLabel.TextColor3 = COLORS.TextDim
	end
end

local function install()
	ChangeHistoryService:SetWaypoint("HelperSasny Install")

	-- 1. RemoteEvent папка
	local remotes = ReplicatedStorage:FindFirstChild("HelperSasnyRemotes")
	if not remotes then
		remotes = Instance.new("Folder")
		remotes.Name = "HelperSasnyRemotes"
		remotes.Parent = ReplicatedStorage
	end
	if not remotes:FindFirstChild("UseFunction") then
		local event = Instance.new("RemoteEvent")
		event.Name = "UseFunction"
		event.Parent = remotes
	end

	-- 2. Сервер
	local oldServer = ServerScriptService:FindFirstChild("HelperSasnyServer")
	if oldServer then oldServer:Destroy() end
	local serverScript = Instance.new("Script")
	serverScript.Name = "HelperSasnyServer"
	serverScript.Source = SERVER_CODE
	serverScript.Parent = ServerScriptService

	-- 3. Клиент
	local playerScripts = StarterPlayer:FindFirstChildOfClass("StarterPlayerScripts")
	if not playerScripts then
		playerScripts = Instance.new("StarterPlayerScripts")
		playerScripts.Parent = StarterPlayer
	end
	local oldClient = playerScripts:FindFirstChild("HelperSasnyClient")
	if oldClient then oldClient:Destroy() end
	local clientScript = Instance.new("LocalScript")
	clientScript.Name = "HelperSasnyClient"
	clientScript.Source = CLIENT_CODE
	clientScript.Parent = playerScripts

	ChangeHistoryService:SetWaypoint("HelperSasny Installed")
	refreshStatus()
	print("[HelperSasny] Установлено! Сервер + Клиент + Магазин готовы. Нажми Play для проверки.")
end

local function uninstall()
	ChangeHistoryService:SetWaypoint("HelperSasny Uninstall")

	local server = ServerScriptService:FindFirstChild("HelperSasnyServer")
	if server then server:Destroy() end

	local playerScripts = StarterPlayer:FindFirstChildOfClass("StarterPlayerScripts")
	if playerScripts then
		local client = playerScripts:FindFirstChild("HelperSasnyClient")
		if client then client:Destroy() end
	end

	local remotes = ReplicatedStorage:FindFirstChild("HelperSasnyRemotes")
	if remotes then remotes:Destroy() end

	ChangeHistoryService:SetWaypoint("HelperSasny Removed")
	refreshStatus()
	print("[HelperSasny] Удалено из игры.")
end

installButton.MouseButton1Click:Connect(install)
removeButton.MouseButton1Click:Connect(uninstall)

button.Click:Connect(function()
	widget.Enabled = not widget.Enabled
end)

refreshStatus()
print("[HelperSasny] Плагин загружен! Нажми кнопку HelperSasny на панели.")
