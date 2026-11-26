-- HelperSasny Client v1.0
-- Клиентская часть: магазин-меню HelperSasny в игре
-- Вставлять в StarterPlayerScripts как LocalScript "HelperSasnyClient"

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")
local TweenService = game:GetService("TweenService")
local workspace = game:GetService("Workspace")
local RunService = game:GetService("RunService")

local player = Players.LocalPlayer
local playerGui = player:WaitForChild("PlayerGui")

-- Ждём папку remote: сервер создаёт её сам при старте (иногда с небольшой задержкой)
local remotesFolder = ReplicatedStorage:FindFirstChild("HelperSasnyRemotes")
while not remotesFolder do
	remotesFolder = ReplicatedStorage:FindFirstChild("HelperSasnyRemotes")
	if remotesFolder then break end
	task.wait(0.3)
end

local useFunctionEvent = remotesFolder:FindFirstChild("UseFunction")
while not useFunctionEvent do
	useFunctionEvent = remotesFolder:FindFirstChild("UseFunction")
	if useFunctionEvent then break end
	task.wait(0.3)
end

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

-- ============================================================
-- СТИКС-ПЕРСОНАЖ: худой стикман, вид «как 2D-картинка» в полный рост,
-- движение заблокировано, кнопка «Жирнее» — анимированное увеличение жирности.
-- ============================================================
local stickmanMode = false
local fatLevel = 0
local MAX_FAT = 10
local stickmanModel = nil
local stickmanParts = {}
local stickmanGui = nil
local originalWalkSpeed = 16
local originalJumpPower = 50
local cameraTweenThread = nil

-- Утилиты для создания части
local function createStickPart(name, shape, size, color, material)
	local part = Instance.new("Part")
	part.Name = name
	part.Shape = shape
	part.Size = size
	part.Color = color
	part.Material = material or Enum.Material.SmoothPlastic
	part.CanCollide = false
	part.CanQuery = false
	part.Anchored = false
	return part
end

-- Создание худого стикмана
local function buildStickman(rootPos)
	local model = Instance.new("Model")
	model.Name = "HelperSasnyStickman"
	model.PrimaryPart = nil

	local torso = createStickPart("Torso", Enum.PartType.Block, Vector3.new(1.0, 1.6, 0.6), COLORS.Accent)
	torso.CFrame = CFrame.new(rootPos + Vector3.new(0, 1.6, 0))
	torso.Parent = model

	local head = createStickPart("Head", Enum.PartType.Block, Vector3.new(0.8, 0.8, 0.8), COLORS.AccentMint)
	head.CFrame = torso.CFrame * CFrame.new(0, 1.6, 0)
	head.Parent = model

	-- Глаза (две точки на лице)
	for _, side in ipairs({-1, 1}) do
		local eye = createStickPart("Eye", Enum.PartType.Ball, Vector3.new(0.14, 0.14, 0.14), Color3.fromRGB(20, 20, 20), Enum.Material.Neon)
		eye.CFrame = head.CFrame * CFrame.new(side * 0.22, 0.1, 0.4)
		eye.Parent = model
	end

	local armSize = Vector3.new(0.3, 1.3, 0.3)
	for _, side in ipairs({-1, 1}) do
		local arm = createStickPart("Arm", Enum.PartType.Cylinder, armSize, COLORS.Accent)
		arm.CFrame = torso.CFrame * CFrame.new(side * 0.85, 0.2, 0)
		arm.Parent = model
	end

	local legSize = Vector3.new(0.36, 1.5, 0.36)
	for _, side in ipairs({-1, 1}) do
		local leg = createStickPart("Leg", Enum.PartType.Cylinder, legSize, COLORS.Accent)
		leg.CFrame = torso.CFrame * CFrame.new(side * 0.3, -1.55, 0)
		leg.Parent = model
	end

	model.Parent = workspace
	stickmanModel = model
	stickmanParts = {
		torso = torso,
		head = head,
		arms = {},
		legs = {},
	}
	-- Собираем ссылки на руки и ноги
	for _, child in ipairs(model:GetChildren()) do
		if child.Name == "Arm" then
			table.insert(stickmanParts.arms, child)
		elseif child.Name == "Leg" then
			table.insert(stickmanParts.legs, child)
		end
	end

	return model
end

-- Применение жирности: анимированное изменение размеров
local function applyFat(level)
	if not stickmanModel then return end
	local torso = stickmanParts.torso
	local head = stickmanParts.head
	if not torso or not head then return end

	local fat = level / MAX_FAT -- 0..1

	-- Цели: торс шире и глубже, голова чуть больше, руки/ноги толще
	local torsoSize = Vector3.new(1.0 + 0.5 * fat, 1.6 - 0.15 * fat, 0.6 + 0.7 * fat)
	local headSize = Vector3.new(0.8 + 0.35 * fat, 0.8 + 0.35 * fat, 0.8 + 0.35 * fat)
	local armSize = Vector3.new(0.3 + 0.35 * fat, 1.3, 0.3 + 0.35 * fat)
	local legSize = Vector3.new(0.36 + 0.45 * fat, 1.5, 0.36 + 0.45 * fat)

	local tweenInfo = TweenInfo.new(0.6, Enum.EasingStyle.Back, Enum.EasingDirection.Out, 1, true)

	TweenService:Create(torso, tweenInfo, { Size = torsoSize }):Play()
	TweenService:Create(head, tweenInfo, { Size = headSize }):Play()

	-- Руки и ноги: размер + перемещение, чтобы держаться за растущий торс
	local armOffsetX = 0.5 + 0.25 * fat + armSize.X / 2
	local legOffsetX = 0.15 + 0.12 * fat
	for _, arm in ipairs(stickmanParts.arms) do
		local side = arm.CFrame.X - torso.Position.X < 0 and -1 or 1
		local targetCF = torso.CFrame * CFrame.new(side * armOffsetX, 0.2, 0)
		local t = TweenService:Create(arm, tweenInfo, { Size = armSize, CFrame = targetCF })
		t:Play()
	end
	for _, leg in ipairs(stickmanParts.legs) do
		local side = leg.CFrame.X - torso.Position.X < 0 and -1 or 1
		local targetCF = torso.CFrame * CFrame.new(side * legOffsetX, -1.55, 0)
		local t = TweenService:Create(leg, tweenInfo, { Size = legSize, CFrame = targetCF })
		t:Play()
	end

	-- Обновляем счётчик
	if fatLabel then
		fatLabel.Text = "Уровень жирности: " .. level .. "/" .. MAX_FAT
	end
end

-- UI-панель стикмана
local fatLabel = nil
local fatButton = nil
local slimButton = nil
local exitButton = nil

local function createStickmanGui()
	if stickmanGui then return end
	stickmanGui = Instance.new("ScreenGui")
	stickmanGui.Name = "HelperSasnyStickman"
	stickmanGui.ResetOnSpawn = false
	stickmanGui.IgnoreGuiInset = true
	stickmanGui.DisplayOrder = 15
	stickmanGui.Parent = playerGui

	local panel = Instance.new("Frame")
	panel.Name = "Panel"
	panel.Size = UDim2.new(0, 240, 0, 190)
	panel.Position = UDim2.new(0, 20, 1, -210)
	panel.BackgroundColor3 = COLORS.Background
	panel.BorderSizePixel = 0
	panel.Parent = stickmanGui

	local panelCorner = Instance.new("UICorner")
	panelCorner.CornerRadius = UDim.new(0, 18)
	panelCorner.Parent = panel

	local panelStroke = Instance.new("UIStroke")
	panelStroke.Thickness = 2
	panelStroke.Color = COLORS.AccentMint
	panelStroke.Parent = panel

	local panelGradient = Instance.new("UIGradient")
	panelGradient.Color = ColorSequence.new(COLORS.Background, COLORS.BackgroundLight)
	panelGradient.Rotation = 90
	panelGradient.Parent = panel

	local title = Instance.new("TextLabel")
	title.Size = UDim2.new(1, 0, 0, 30)
	title.Position = UDim2.new(0, 12, 0, 12)
	title.BackgroundTransparency = 1
	title.Text = "🖥 Стикс-экран"
	title.Font = Enum.Font.GothamBlack
	title.TextSize = 16
	title.TextColor3 = COLORS.AccentMint
	title.Parent = panel

	fatLabel = Instance.new("TextLabel")
	fatLabel.Size = UDim2.new(1, 0, 0, 26)
	fatLabel.Position = UDim2.new(0, 12, 0, 46)
	fatLabel.BackgroundTransparency = 1
	fatLabel.Text = "Уровень жирности: 0/" .. MAX_FAT
	fatLabel.Font = Enum.Font.GothamBold
	fatLabel.TextSize = 13
	fatLabel.TextColor3 = COLORS.Text
	fatLabel.Parent = panel

	fatButton = Instance.new("TextButton")
	fatButton.Size = UDim2.new(1, -20, 0, 48)
	fatButton.Position = UDim2.new(0, 10, 0, 80)
	fatButton.BackgroundColor3 = COLORS.Accent
	fatButton.Text = "🍔 Жирнее"
	fatButton.Font = Enum.Font.GothamBlack
	fatButton.TextSize = 16
	fatButton.TextColor3 = Color3.fromRGB(255, 255, 255)
	fatButton.AutoButtonColor = false
	fatButton.Parent = panel

	local fatCorner = Instance.new("UICorner")
	fatCorner.CornerRadius = UDim.new(0, 12)
	fatCorner.Parent = fatButton

	local fatStroke = Instance.new("UIStroke")
	fatStroke.Thickness = 2
	fatStroke.Color = COLORS.AccentMint
	fatStroke.Parent = fatButton

	slimButton = Instance.new("TextButton")
	slimButton.Size = UDim2.new(1, -20, 0, 42)
	slimButton.Position = UDim2.new(0, 10, 0, 138)
	slimButton.BackgroundColor3 = COLORS.BackgroundLight
	slimButton.Text = "🥗 Похудеть"
	slimButton.Font = Enum.Font.GothamBold
	slimButton.TextSize = 14
	slimButton.TextColor3 = COLORS.Text
	slimButton.AutoButtonColor = false
	slimButton.Parent = panel

	local slimCorner = Instance.new("UICorner")
	slimCorner.CornerRadius = UDim.new(0, 10)
	slimCorner.Parent = slimButton

	exitButton = Instance.new("TextButton")
	exitButton.Size = UDim2.new(0, 90, 0, 34)
	exitButton.Position = UDim2.new(1, -100, 0, 8)
	exitButton.BackgroundColor3 = Color3.fromRGB(80, 55, 90)
	exitButton.Text = "✕ Выйти"
	exitButton.Font = Enum.Font.GothamBold
	exitButton.TextSize = 12
	exitButton.TextColor3 = COLORS.Text
	exitButton.AutoButtonColor = false
	exitButton.Parent = panel

	local exitCorner = Instance.new("UICorner")
	exitCorner.CornerRadius = UDim.new(0, 10)
	exitCorner.Parent = exitButton

	fatButton.MouseButton1Click:Connect(function()
		if fatLevel < MAX_FAT then
			fatLevel = fatLevel + 1
			applyFat(fatLevel)
			showToast("🍔 Жирнее! Уровень: " .. fatLevel)
		end
	end)

	slimButton.MouseButton1Click:Connect(function()
		if fatLevel > 0 then
			fatLevel = fatLevel - 1
			applyFat(fatLevel)
			showToast("🥗 Похудел! Уровень: " .. fatLevel)
		end
	end)

	exitButton.MouseButton1Click:Connect(stopStickmanMode)
end

-- Запуск режима стикмана
local function startStickmanMode()
	if stickmanMode then return end
	local character = player.Character
	if not character then return end
	local humanoid = character:FindFirstChildOfClass("Humanoid")
	local root = character:FindFirstChild("HumanoidRootPart")
	if not root then return end

	-- Сохраняем и блокируем движение
	if humanoid then
		originalWalkSpeed = humanoid.WalkSpeed
		originalJumpPower = humanoid.JumpPower
		humanoid.WalkSpeed = 0
		humanoid.JumpPower = 0
		humanoid:ChangeState(Enum.HumanoidStateType.Standing)
	end

	-- Скрываем оригинальное тело персонажа
	for _, part in ipairs(character:GetChildren()) do
		if part:IsA("Part") or part:IsA("MeshPart") then
			part.Transparency = 1
			part.CanCollide = false
		end
	end

	-- Создаём стикмана на месте персонажа
	buildStickman(root.Position)

	-- UI
	createStickmanGui()

	-- Локатор камеры
	local cam = workspace.CurrentCamera
	cam.CameraMode = Enum.CameraMode.Scriptable

	stickmanMode = true
	applyFat(fatLevel)

	-- Цикл фиксации камеры: вид на стикмана в полный рост, как 2D-картинка
	if cameraTweenThread then task.cancel(cameraTweenThread) end
	cameraTweenThread = task.spawn(function()
		while stickmanMode and stickmanModel do
			local torso = stickmanParts.torso
			if torso and torso.Parent then
				local camPos = torso.Position + Vector3.new(0, 1.2, 11)
				local lookAt = torso.Position + Vector3.new(0, 1.6, 0)
				cam.CFrame = CFrame.lookAt(camPos, lookAt)
				cam.FieldOfView = 60
			end
			RunService.Heartbeat:Wait()
		end
	end)
end

-- Выход из режима
local function stopStickmanMode()
	if not stickmanMode then return end
	stickmanMode = false

	if cameraTweenThread then
		task.cancel(cameraTweenThread)
		cameraTweenThread = nil
	end

	-- Восстанавливаем камеру
	local cam = workspace.CurrentCamera
	cam.CameraMode = Enum.CameraMode.Default
	cam.FieldOfView = 70

	-- Удаляем стикмана
	if stickmanModel then
		stickmanModel:Destroy()
		stickmanModel = nil
	end
	stickmanParts = {}

	-- Восстанавливаем персонажа
	local character = player.Character
	if character then
		local humanoid = character:FindFirstChildOfClass("Humanoid")
		if humanoid then
			humanoid.WalkSpeed = originalWalkSpeed
			humanoid.JumpPower = originalJumpPower
		end
		for _, part in ipairs(character:GetChildren()) do
			if part:IsA("Part") or part:IsA("MeshPart") then
				part.Transparency = 0
				part.CanCollide = true
			end
		end
	end

	-- Удаляем UI
	if stickmanGui then
		stickmanGui:Destroy()
		stickmanGui = nil
	end
	fatLabel = nil
	fatButton = nil
	slimButton = nil
	exitButton = nil
end

-- Запуск при загрузке персонажа
player.CharacterAdded:Connect(function(character)
	task.spawn(function()
		-- Небольшая пауза, чтобы модель полностью сложилась
		task.wait(0.5)
		startStickmanMode()
	end)
end)

player.CharacterRemoving:Connect(function()
	stopStickmanMode()
end)

print("[HelperSasny] Клиент загружен! Магазин готов")
