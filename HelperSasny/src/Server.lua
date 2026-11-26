-- HelperSasny Server v1.0
-- Серверная часть: обрабатывает все функции магазина HelperSasny
-- Вставлять в ServerScriptService как Script "HelperSasnyServer"

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
