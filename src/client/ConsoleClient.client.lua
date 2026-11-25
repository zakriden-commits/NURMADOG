--!strict

-- Client presentation layer:
-- * centre-screen raycast so the prompt only appears while looking at the console;
-- * hold-to-power interaction with server-side timing validation;
-- * a local, cinematic camera sequence followed by the requested blackout.

local ContextActionService = game:GetService("ContextActionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")
local Workspace = game:GetService("Workspace")

local player = Players.LocalPlayer
local playerGui = player:WaitForChild("PlayerGui")

local shared = ReplicatedStorage:WaitForChild("PS5BootShared")
local Config = require(shared:WaitForChild("ConsoleConfig"))

local remotes = ReplicatedStorage:WaitForChild("PS5BootRemotes")
local interactionEvent = remotes:WaitForChild("Interaction") :: RemoteEvent
local cinematicEvent = remotes:WaitForChild("Cinematic") :: RemoteEvent
local consoleReference = remotes:WaitForChild("ConsoleModel") :: ObjectValue

local function waitForConsole(): Model
	local value = consoleReference.Value
	while not value do
		consoleReference:GetPropertyChangedSignal("Value"):Wait()
		value = consoleReference.Value
	end

	assert(value:IsA("Model"), "PS5BootRemotes.ConsoleModel must reference a Model")
	return value
end

local console = waitForConsole()
local interactionTarget = console:FindFirstChild("InteractionTarget", true)
assert(interactionTarget and interactionTarget:IsA("BasePart"), "PS5 console is missing InteractionTarget")

local previousHud = playerGui:FindFirstChild("PS5BootHUD")
if previousHud then
	previousHud:Destroy()
end

local function addCorner(parent: Instance, radius: number)
	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, radius)
	corner.Parent = parent
end

local function addStroke(parent: Instance, color: Color3, transparency: number, thickness: number)
	local stroke = Instance.new("UIStroke")
	stroke.Color = color
	stroke.Transparency = transparency
	stroke.Thickness = thickness
	stroke.Parent = parent
end

local function tween(instance: Instance, duration: number, properties: { [string]: any }, style: Enum.EasingStyle?): Tween
	local animation = TweenService:Create(
		instance,
		TweenInfo.new(duration, style or Enum.EasingStyle.Quint, Enum.EasingDirection.Out),
		properties
	)
	animation:Play()
	return animation
end

-- HUD -----------------------------------------------------------------------

local hud = Instance.new("ScreenGui")
hud.Name = "PS5BootHUD"
hud.IgnoreGuiInset = true
hud.ResetOnSpawn = false
hud.DisplayOrder = 100
hud.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
hud.Parent = playerGui

local reticle = Instance.new("Frame")
reticle.Name = "Reticle"
reticle.AnchorPoint = Vector2.new(0.5, 0.5)
reticle.Position = UDim2.fromScale(0.5, 0.5)
reticle.Size = UDim2.fromOffset(38, 38)
reticle.BackgroundTransparency = 1
reticle.ZIndex = 2
reticle.Parent = hud

local reticlePieces: { Frame } = {}
local function reticlePiece(name: string, position: UDim2, size: UDim2)
	local piece = Instance.new("Frame")
	piece.Name = name
	piece.Position = position
	piece.Size = size
	piece.BorderSizePixel = 0
	piece.BackgroundColor3 = Color3.fromRGB(163, 182, 205)
	piece.BackgroundTransparency = 0.24
	piece.ZIndex = 2
	piece.Parent = reticle
	table.insert(reticlePieces, piece)
end

reticlePiece("Top", UDim2.fromOffset(17, 0), UDim2.fromOffset(4, 9))
reticlePiece("Bottom", UDim2.fromOffset(17, 29), UDim2.fromOffset(4, 9))
reticlePiece("Left", UDim2.fromOffset(0, 17), UDim2.fromOffset(9, 4))
reticlePiece("Right", UDim2.fromOffset(29, 17), UDim2.fromOffset(9, 4))

local reticleDot = Instance.new("Frame")
reticleDot.Name = "Dot"
reticleDot.AnchorPoint = Vector2.new(0.5, 0.5)
reticleDot.Position = UDim2.fromScale(0.5, 0.5)
reticleDot.Size = UDim2.fromOffset(4, 4)
reticleDot.BackgroundColor3 = Color3.fromRGB(163, 182, 205)
reticleDot.BackgroundTransparency = 0.15
reticleDot.BorderSizePixel = 0
reticleDot.ZIndex = 2
reticleDot.Parent = reticle
addCorner(reticleDot, 8)

local promptGroup = Instance.new("CanvasGroup")
promptGroup.Name = "InteractionPrompt"
promptGroup.AnchorPoint = Vector2.new(0.5, 1)
promptGroup.Position = UDim2.fromScale(0.5, 0.86)
promptGroup.Size = UDim2.fromOffset(448, 128)
promptGroup.BackgroundTransparency = 1
promptGroup.GroupTransparency = 1
promptGroup.Visible = false
promptGroup.ZIndex = 5
promptGroup.Parent = hud

local promptPanel = Instance.new("Frame")
promptPanel.Name = "Panel"
promptPanel.Size = UDim2.fromScale(1, 1)
promptPanel.BackgroundColor3 = Color3.fromRGB(7, 13, 23)
promptPanel.BackgroundTransparency = 0.07
promptPanel.BorderSizePixel = 0
promptPanel.ZIndex = 5
promptPanel.Parent = promptGroup
addCorner(promptPanel, 14)
addStroke(promptPanel, Color3.fromRGB(86, 156, 223), 0.34, 1)

local panelGradient = Instance.new("UIGradient")
panelGradient.Color = ColorSequence.new({
	ColorSequenceKeypoint.new(0, Color3.fromRGB(16, 28, 44)),
	ColorSequenceKeypoint.new(1, Color3.fromRGB(5, 9, 16)),
})
panelGradient.Rotation = 90
panelGradient.Parent = promptPanel

local accent = Instance.new("Frame")
accent.Name = "Accent"
accent.Position = UDim2.fromOffset(18, 15)
accent.Size = UDim2.fromOffset(3, 61)
accent.BackgroundColor3 = Color3.fromRGB(79, 180, 255)
accent.BorderSizePixel = 0
accent.ZIndex = 6
accent.Parent = promptPanel
addCorner(accent, 3)

local promptTitle = Instance.new("TextLabel")
promptTitle.Name = "Title"
promptTitle.Position = UDim2.fromOffset(37, 15)
promptTitle.Size = UDim2.fromOffset(280, 23)
promptTitle.BackgroundTransparency = 1
promptTitle.Font = Enum.Font.GothamBold
promptTitle.Text = "PLAYSTATION 5"
promptTitle.TextColor3 = Color3.fromRGB(236, 245, 255)
promptTitle.TextSize = 16
promptTitle.TextXAlignment = Enum.TextXAlignment.Left
promptTitle.ZIndex = 6
promptTitle.Parent = promptPanel

local promptSubTitle = Instance.new("TextLabel")
promptSubTitle.Name = "SubTitle"
promptSubTitle.Position = UDim2.fromOffset(37, 40)
promptSubTitle.Size = UDim2.fromOffset(300, 18)
promptSubTitle.BackgroundTransparency = 1
promptSubTitle.Font = Enum.Font.Gotham
promptSubTitle.Text = "КОНСОЛЬ ОЖИДАЕТ ЗАПУСКА"
promptSubTitle.TextColor3 = Color3.fromRGB(139, 166, 195)
promptSubTitle.TextSize = 11
promptSubTitle.TextXAlignment = Enum.TextXAlignment.Left
promptSubTitle.ZIndex = 6
promptSubTitle.Parent = promptPanel

local keyCap = Instance.new("Frame")
keyCap.Name = "KeyCap"
keyCap.AnchorPoint = Vector2.new(1, 0)
keyCap.Position = UDim2.new(1, -18, 0, 17)
keyCap.Size = UDim2.fromOffset(53, 37)
keyCap.BackgroundColor3 = Color3.fromRGB(30, 51, 76)
keyCap.BorderSizePixel = 0
keyCap.ZIndex = 6
keyCap.Parent = promptPanel
addCorner(keyCap, 8)
addStroke(keyCap, Color3.fromRGB(129, 194, 255), 0.22, 1)

local keyCapText = Instance.new("TextLabel")
keyCapText.Size = UDim2.fromScale(1, 1)
keyCapText.BackgroundTransparency = 1
keyCapText.Font = Enum.Font.GothamBold
keyCapText.Text = "E"
keyCapText.TextColor3 = Color3.fromRGB(239, 248, 255)
keyCapText.TextSize = 17
keyCapText.ZIndex = 7
keyCapText.Parent = keyCap

local instruction = Instance.new("TextLabel")
instruction.Name = "Instruction"
instruction.Position = UDim2.fromOffset(37, 67)
instruction.Size = UDim2.fromOffset(370, 19)
instruction.BackgroundTransparency = 1
instruction.Font = Enum.Font.GothamMedium
instruction.Text = "УДЕРЖИВАЙТЕ, ЧТОБЫ ВКЛЮЧИТЬ"
instruction.TextColor3 = Color3.fromRGB(223, 234, 247)
instruction.TextSize = 12
instruction.TextXAlignment = Enum.TextXAlignment.Left
instruction.ZIndex = 6
instruction.Parent = promptPanel

local statusLabel = Instance.new("TextLabel")
statusLabel.Name = "Status"
statusLabel.Position = UDim2.new(1, -177, 0, 68)
statusLabel.Size = UDim2.fromOffset(140, 18)
statusLabel.BackgroundTransparency = 1
statusLabel.Font = Enum.Font.Gotham
statusLabel.Text = "ГОТОВО"
statusLabel.TextColor3 = Color3.fromRGB(91, 181, 255)
statusLabel.TextSize = 10
statusLabel.TextXAlignment = Enum.TextXAlignment.Right
statusLabel.ZIndex = 6
statusLabel.Parent = promptPanel

local progressBack = Instance.new("Frame")
progressBack.Name = "ProgressBack"
progressBack.Position = UDim2.new(0, 18, 1, -18)
progressBack.Size = UDim2.new(1, -36, 0, 4)
progressBack.BackgroundColor3 = Color3.fromRGB(45, 60, 79)
progressBack.BackgroundTransparency = 0.1
progressBack.BorderSizePixel = 0
progressBack.ZIndex = 6
progressBack.Parent = promptPanel
addCorner(progressBack, 4)

local progressFill = Instance.new("Frame")
progressFill.Name = "ProgressFill"
progressFill.Size = UDim2.fromScale(0, 1)
progressFill.BackgroundColor3 = Color3.fromRGB(72, 181, 255)
progressFill.BorderSizePixel = 0
progressFill.ZIndex = 7
progressFill.Parent = progressBack
addCorner(progressFill, 4)

local fillGradient = Instance.new("UIGradient")
fillGradient.Color = ColorSequence.new({
	ColorSequenceKeypoint.new(0, Color3.fromRGB(54, 129, 255)),
	ColorSequenceKeypoint.new(1, Color3.fromRGB(118, 223, 255)),
})
fillGradient.Parent = progressFill

-- Cinematic overlay. It is fully local: other players keep normal control.
local fade = Instance.new("Frame")
fade.Name = "CinematicFade"
fade.Size = UDim2.fromScale(1, 1)
fade.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
fade.BackgroundTransparency = 1
fade.BorderSizePixel = 0
fade.ZIndex = 20
fade.Parent = hud

local topBar = Instance.new("Frame")
topBar.Name = "LetterboxTop"
topBar.Position = UDim2.fromScale(0, -0.12)
topBar.Size = UDim2.fromScale(1, 0.12)
topBar.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
topBar.BorderSizePixel = 0
topBar.ZIndex = 21
topBar.Parent = hud

local bottomBar = Instance.new("Frame")
bottomBar.Name = "LetterboxBottom"
bottomBar.Position = UDim2.fromScale(0, 1)
bottomBar.Size = UDim2.fromScale(1, 0.12)
bottomBar.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
bottomBar.BorderSizePixel = 0
bottomBar.ZIndex = 21
bottomBar.Parent = hud

local cinematicCaption = Instance.new("TextLabel")
cinematicCaption.Name = "CinematicCaption"
cinematicCaption.AnchorPoint = Vector2.new(0.5, 1)
cinematicCaption.Position = UDim2.fromScale(0.5, 0.84)
cinematicCaption.Size = UDim2.fromOffset(640, 32)
cinematicCaption.BackgroundTransparency = 1
cinematicCaption.Font = Enum.Font.GothamMedium
cinematicCaption.Text = ""
cinematicCaption.TextColor3 = Color3.fromRGB(226, 239, 255)
cinematicCaption.TextSize = 13
cinematicCaption.TextTransparency = 1
cinematicCaption.TextStrokeTransparency = 0.55
cinematicCaption.TextXAlignment = Enum.TextXAlignment.Center
cinematicCaption.ZIndex = 22
cinematicCaption.Parent = hud

local focusHighlight = Instance.new("Highlight")
focusHighlight.Name = "LocalConsoleFocus"
focusHighlight.Adornee = console
focusHighlight.DepthMode = Enum.HighlightDepthMode.Occluded
focusHighlight.FillColor = Color3.fromRGB(48, 137, 255)
focusHighlight.FillTransparency = 0.90
focusHighlight.OutlineColor = Color3.fromRGB(119, 204, 255)
focusHighlight.OutlineTransparency = 0.12
focusHighlight.Enabled = false
focusHighlight.Parent = Workspace

-- Interaction ---------------------------------------------------------------

local isFocused = false
local promptVisible = false
local holding = false
local completionSent = false
local cinematicActive = false
local holdToken = 0
local holdTween: Tween? = nil

local function setReticleFocused(focused: boolean)
	local color = if focused then Color3.fromRGB(103, 205, 255) else Color3.fromRGB(163, 182, 205)
	local transparency = if focused then 0 else 0.24
	for _, piece in reticlePieces do
		piece.BackgroundColor3 = color
		piece.BackgroundTransparency = transparency
	end
	reticleDot.BackgroundColor3 = color
	reticleDot.BackgroundTransparency = if focused then 0 else 0.15
end

local function setPromptVisible(visible: boolean)
	if promptVisible == visible then
		return
	end

	promptVisible = visible
	if visible then
		promptGroup.Visible = true
		tween(promptGroup, 0.16, { GroupTransparency = 0 }, Enum.EasingStyle.Quad)
	else
		tween(promptGroup, 0.12, { GroupTransparency = 1 }, Enum.EasingStyle.Quad)
		task.delay(0.13, function()
			if not promptVisible then
				promptGroup.Visible = false
			end
		end)
	end
end

local function resetPromptText()
	instruction.Text = "УДЕРЖИВАЙТЕ, ЧТОБЫ ВКЛЮЧИТЬ"
	statusLabel.Text = "ГОТОВО"
	statusLabel.TextColor3 = Color3.fromRGB(91, 181, 255)
end

local function stopProgress()
	if holdTween then
		holdTween:Cancel()
		holdTween = nil
	end
	progressFill.Size = UDim2.fromScale(0, 1)
end

local function cancelHold(notifyServer: boolean)
	if not holding and not completionSent then
		return
	end

	local shouldNotify = holding and not completionSent
	holding = false
	completionSent = false
	holdToken += 1
	stopProgress()
	resetPromptText()

	if notifyServer and shouldNotify then
		interactionEvent:FireServer("Cancel")
	end
end

local function beginHold()
	if holding or completionSent or cinematicActive then
		return
	end

	holding = true
	completionSent = false
	holdToken += 1
	local token = holdToken

	instruction.Text = "НЕ ОТПУСКАЙТЕ КЛАВИШУ"
	statusLabel.Text = "ПРОВЕРКА ПИТАНИЯ"
	statusLabel.TextColor3 = Color3.fromRGB(154, 217, 255)
	progressFill.Size = UDim2.fromScale(0, 1)
	interactionEvent:FireServer("Begin")

	holdTween = tween(
		progressFill,
		Config.Interaction.HoldDuration,
		{ Size = UDim2.fromScale(1, 1) },
		Enum.EasingStyle.Linear
	)

	holdTween.Completed:Connect(function(playbackState)
		if playbackState ~= Enum.PlaybackState.Completed then
			return
		end
		if token ~= holdToken or not holding or completionSent then
			return
		end

		completionSent = true
		instruction.Text = "СИГНАЛ ПРИНЯТ"
		statusLabel.Text = "ЗАПУСК"
		statusLabel.TextColor3 = Color3.fromRGB(143, 225, 255)
		interactionEvent:FireServer("Complete")
	end)
end

local function setFocus(focused: boolean)
	if isFocused == focused then
		return
	end

	isFocused = focused
	focusHighlight.Enabled = focused
	setReticleFocused(focused)
	setPromptVisible(focused and not cinematicActive)

	if not focused and holding and not completionSent then
		cancelHold(true)
	end
end

local function isConsoleInCrosshair(): boolean
	if cinematicActive or console:GetAttribute("ConsoleState") ~= "Offline" then
		return false
	end

	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart")
	if not root or not root:IsA("BasePart") then
		return false
	end

	if (root.Position - interactionTarget.Position).Magnitude > Config.Interaction.MaxDistance then
		return false
	end

	local camera = Workspace.CurrentCamera
	if not camera then
		return false
	end

	local viewport = camera.ViewportSize
	local unitRay = camera:ViewportPointToRay(viewport.X * 0.5, viewport.Y * 0.5)
	local raycastParams = RaycastParams.new()
	raycastParams.FilterType = Enum.RaycastFilterType.Exclude
	raycastParams.FilterDescendantsInstances = { character }
	raycastParams.IgnoreWater = true

	local result = Workspace:Raycast(unitRay.Origin, unitRay.Direction * 32, raycastParams)
	return result ~= nil and result.Instance:IsDescendantOf(console)
end

local function interactionAction(
	_actionName: string,
	inputState: Enum.UserInputState,
	_inputObject: InputObject
): Enum.ContextActionResult
	if cinematicActive then
		return Enum.ContextActionResult.Pass
	end

	if inputState == Enum.UserInputState.Begin then
		if isFocused and console:GetAttribute("ConsoleState") == "Offline" then
			beginHold()
			return Enum.ContextActionResult.Sink
		end
		return Enum.ContextActionResult.Pass
	end

	if inputState == Enum.UserInputState.End or inputState == Enum.UserInputState.Cancel then
		if holding then
			if not completionSent then
				cancelHold(true)
			end
			return Enum.ContextActionResult.Sink
		end
	end

	return Enum.ContextActionResult.Pass
end

ContextActionService:BindActionAtPriority(
	"PS5BootExperience_HoldPower",
	interactionAction,
	false,
	3000,
	Enum.KeyCode.E,
	Enum.KeyCode.ButtonX
)

-- Camera / cinematic --------------------------------------------------------

local savedCameraType: Enum.CameraType? = nil
local savedCameraSubject: Instance? = nil
local savedFieldOfView: number? = nil
local savedMouseBehavior: Enum.MouseBehavior? = nil
local savedMouseIconEnabled: boolean? = nil
local localControls: any = nil

local function lockPlayerForCinematic(camera: Camera)
	savedCameraType = camera.CameraType
	savedCameraSubject = camera.CameraSubject
	savedFieldOfView = camera.FieldOfView
	savedMouseBehavior = UserInputService.MouseBehavior
	savedMouseIconEnabled = UserInputService.MouseIconEnabled

	local playerScripts = player:FindFirstChild("PlayerScripts")
	local playerModule = playerScripts and playerScripts:FindFirstChild("PlayerModule")
	if playerModule and playerModule:IsA("ModuleScript") then
		local success, module = pcall(require, playerModule)
		if success then
			local moduleAny = module :: any
			if type(moduleAny) == "table" and type(moduleAny.GetControls) == "function" then
				localControls = moduleAny:GetControls()
				if localControls and type(localControls.Disable) == "function" then
					localControls:Disable()
				end
			end
		end
	end

	UserInputService.MouseBehavior = Enum.MouseBehavior.Default
	UserInputService.MouseIconEnabled = false
	camera.CameraType = Enum.CameraType.Scriptable
end

local function restoreAfterCinematic(camera: Camera)
	if savedCameraType then
		camera.CameraType = savedCameraType
	end
	if savedCameraSubject then
		camera.CameraSubject = savedCameraSubject
	end
	if savedFieldOfView then
		camera.FieldOfView = savedFieldOfView
	end
	if savedMouseBehavior then
		UserInputService.MouseBehavior = savedMouseBehavior
	end
	if savedMouseIconEnabled ~= nil then
		UserInputService.MouseIconEnabled = savedMouseIconEnabled
	end
	if localControls and type(localControls.Enable) == "function" then
		localControls:Enable()
	end
	localControls = nil
end

local function waitForOffset(startAt: number, offset: number)
	local remaining = startAt + offset - Workspace:GetServerTimeNow()
	if remaining > 0 then
		task.wait(remaining)
	end
end

local function cinematicFrame(rootCFrame: CFrame, cameraOffset: Vector3, focusOffset: Vector3): CFrame
	return CFrame.lookAt(
		rootCFrame:PointToWorldSpace(cameraOffset),
		rootCFrame:PointToWorldSpace(focusOffset)
	)
end

local function showCaption(text: string)
	cinematicCaption.Text = text
	tween(cinematicCaption, 0.22, { TextTransparency = 0.10 }, Enum.EasingStyle.Quad)
end

local function hideCaption()
	tween(cinematicCaption, 0.20, { TextTransparency = 1 }, Enum.EasingStyle.Quad)
end

local function playCinematic(startAt: number)
	if cinematicActive then
		return
	end
	cinematicActive = true
	cancelHold(false)
	setFocus(false)
	setPromptVisible(false)

	local camera = Workspace.CurrentCamera
	local root = console.PrimaryPart
	if not camera or not root then
		-- Do not leave input in a permanently disabled state if a custom map
		-- removes the console/camera during a transition.
		cinematicActive = false
		return
	end

	-- Cover the camera handoff first, then synchronize visuals with server time.
	fade.BackgroundTransparency = 0
	fade.Visible = true
	lockPlayerForCinematic(camera)

	waitForOffset(startAt, 0)
	local rootCFrame = root.CFrame
	local wide = cinematicFrame(rootCFrame, Vector3.new(6.8, 4.3, -8.8), Vector3.new(0, 3.05, -0.45))
	local front = cinematicFrame(rootCFrame, Vector3.new(2.9, 3.25, -5.3), Vector3.new(0, 3.15, -1.10))
	local detail = cinematicFrame(rootCFrame, Vector3.new(-2.15, 3.55, -4.25), Vector3.new(0, 3.36, -1.28))
	local hero = cinematicFrame(rootCFrame, Vector3.new(-5.1, 4.8, -7.0), Vector3.new(0, 3.15, -0.20))

	camera.CFrame = wide
	camera.FieldOfView = 56
	tween(topBar, 0.42, { Position = UDim2.fromScale(0, 0) }, Enum.EasingStyle.Quart)
	tween(bottomBar, 0.42, { Position = UDim2.fromScale(0, 0.88) }, Enum.EasingStyle.Quart)
	showCaption("ВКЛЮЧЕНИЕ СИСТЕМЫ")
	tween(fade, 0.55, { BackgroundTransparency = 0.12 }, Enum.EasingStyle.Quad)
	tween(camera, 1.72, { CFrame = front, FieldOfView = 49 }, Enum.EasingStyle.Quart)

	waitForOffset(startAt, 1.72)
	showCaption("ПИТАНИЕ ПОДАНО")
	tween(camera, 1.62, { CFrame = detail, FieldOfView = 43 }, Enum.EasingStyle.Quart)

	waitForOffset(startAt, 3.34)
	showCaption("ИНИЦИАЛИЗАЦИЯ ЯДРА")
	tween(camera, 1.78, { CFrame = hero, FieldOfView = 52 }, Enum.EasingStyle.Quart)

	waitForOffset(startAt, 5.12)
	hideCaption()
	local fadeStart = math.max(5.15, Config.Cinematic.BlackoutAt - 0.72)
	waitForOffset(startAt, fadeStart)
	tween(fade, Config.Cinematic.BlackoutAt - fadeStart, { BackgroundTransparency = 0 }, Enum.EasingStyle.Quad)

	waitForOffset(startAt, Config.Cinematic.BlackoutAt)
	cinematicCaption.Text = ""
	topBar.Position = UDim2.fromScale(0, 0)
	bottomBar.Position = UDim2.fromScale(0, 0.88)

	-- Default is intentionally persistent: the requested ending is pure darkness.
	-- Set BlackoutPersistenceSeconds in ConsoleConfig to a positive value when a
	-- game should return control instead of teleporting/loading another scene here.
	if Config.Cinematic.BlackoutPersistenceSeconds > 0 then
		task.wait(Config.Cinematic.BlackoutPersistenceSeconds)
		tween(fade, 0.55, { BackgroundTransparency = 1 }, Enum.EasingStyle.Quad)
		tween(topBar, 0.35, { Position = UDim2.fromScale(0, -0.12) }, Enum.EasingStyle.Quad)
		tween(bottomBar, 0.35, { Position = UDim2.fromScale(0, 1) }, Enum.EasingStyle.Quad)
		task.wait(0.56)
		restoreAfterCinematic(camera)
		cinematicActive = false
	end
end

-- Replicated state is used as a fallback so every client promptly loses the
-- prompt when another player has already started the console.
console:GetAttributeChangedSignal("ConsoleState"):Connect(function()
	if console:GetAttribute("ConsoleState") ~= "Offline" then
		setFocus(false)
		setPromptVisible(false)
	end
end)

interactionEvent.OnClientEvent:Connect(function(message: unknown)
	if message == "HoldDenied" then
		cancelHold(false)
	elseif message == "BootAccepted" then
		holding = false
		completionSent = false
		if holdTween then
			holdTween:Cancel()
			holdTween = nil
		end
	end
end)

cinematicEvent.OnClientEvent:Connect(function(message: unknown, startAt: unknown)
	if message == "Start" and type(startAt) == "number" then
		task.spawn(playCinematic, startAt)
	end
end)

RunService:BindToRenderStep("PS5BootExperience_AimCheck", Enum.RenderPriority.Camera.Value + 1, function()
	setFocus(isConsoleInCrosshair())
end)

script.Destroying:Connect(function()
	ContextActionService:UnbindAction("PS5BootExperience_HoldPower")
	RunService:UnbindFromRenderStep("PS5BootExperience_AimCheck")
	focusHighlight:Destroy()
end)
