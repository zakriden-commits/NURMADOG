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
