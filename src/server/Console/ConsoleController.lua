--!strict

-- Server-authoritative interaction and physical power-on animation.
-- The client is allowed to request a hold, but the server owns distance, timing,
-- state transitions, and the cinematic start timestamp.

local Players = game:GetService("Players")
local TweenService = game:GetService("TweenService")
local Workspace = game:GetService("Workspace")

local ConsoleController = {}
ConsoleController.__index = ConsoleController

type InteractionConfig = {
	MaxDistance: number,
	HoldDuration: number,
	HoldLeeway: number,
	ServerGraceDistance: number,
}

type CinematicConfig = {
	StartLeadTime: number,
	BlackoutAt: number,
}

type ControllerConfig = {
	Interaction: InteractionConfig,
	Cinematic: CinematicConfig,
}

type ConsoleState = "Offline" | "Booting" | "Online"

type HoldRecord = {
	startedAt: number,
}

export type ConsoleController = {
	_model: Model,
	_config: ControllerConfig,
	_interactionEvent: RemoteEvent,
	_cinematicEvent: RemoteEvent,
	_interactionTarget: BasePart,
	_leftPanel: BasePart,
	_rightPanel: BasePart,
	_led: BasePart,
	_powerGlow: PointLight,
	_bootSound: Sound?,
	_homePanels: { [BasePart]: CFrame },
	_state: ConsoleState,
	_holdOwner: Player?,
	_holds: { [Player]: HoldRecord },
	connections: { RBXScriptConnection },
	Start: (self: ConsoleController) -> (),
	Destroy: (self: ConsoleController) -> (),
}

local OFF_COLOR = Color3.fromRGB(3, 16, 33)
local START_COLOR = Color3.fromRGB(23, 94, 178)
local ACTIVE_COLOR = Color3.fromRGB(72, 183, 255)

local function expectBasePart(model: Model, name: string): BasePart
	local instance = model:FindFirstChild(name, true)
	assert(instance and instance:IsA("BasePart"), string.format("PS5 console is missing BasePart %q", name))
	return instance
end

local function expectPointLight(parent: Instance, name: string): PointLight
	local instance = parent:FindFirstChild(name)
	assert(instance and instance:IsA("PointLight"), string.format("PS5 console is missing PointLight %q", name))
	return instance
end

local function asState(value: unknown): ConsoleState
	if value == "Booting" or value == "Online" then
		return value
	end

	return "Offline"
end

function ConsoleController.new(
	model: Model,
	config: ControllerConfig,
	interactionEvent: RemoteEvent,
	cinematicEvent: RemoteEvent
): ConsoleController
	local led = expectBasePart(model, "PowerLed")
	local leftPanel = expectBasePart(model, "PanelLeft")
	local rightPanel = expectBasePart(model, "PanelRight")
	local root = model.PrimaryPart
	assert(root, "PS5 console model must have a PrimaryPart")
	local soundCandidate = root:FindFirstChild("PowerOnSfx")
	local bootSound = if soundCandidate and soundCandidate:IsA("Sound") then soundCandidate else nil

	local self = setmetatable({
		_model = model,
		_config = config,
		_interactionEvent = interactionEvent,
		_cinematicEvent = cinematicEvent,
		_interactionTarget = expectBasePart(model, "InteractionTarget"),
		_leftPanel = leftPanel,
		_rightPanel = rightPanel,
		_led = led,
		_powerGlow = expectPointLight(led, "PowerGlow"),
		_bootSound = bootSound,
		_homePanels = {
			[leftPanel] = leftPanel.CFrame,
			[rightPanel] = rightPanel.CFrame,
		},
		_state = asState(model:GetAttribute("ConsoleState")),
		_holdOwner = nil,
		_holds = {},
		connections = {},
	}, ConsoleController)

	return self
end

function ConsoleController:_setState(state: ConsoleState)
	self._state = state
	self._model:SetAttribute("ConsoleState", state)
end

function ConsoleController:_setOfflineVisuals()
	self._led.Color = OFF_COLOR
	self._led.Material = Enum.Material.Neon
	self._powerGlow.Color = ACTIVE_COLOR
	self._powerGlow.Brightness = 0
	self._powerGlow.Range = 0

	for panel, homeCFrame in self._homePanels do
		panel.CFrame = homeCFrame
	end
end

function ConsoleController:_tween(instance: Instance, duration: number, properties: { [string]: any }): Tween
	local tween = TweenService:Create(
		instance,
		TweenInfo.new(duration, Enum.EasingStyle.Quint, Enum.EasingDirection.Out),
		properties
	)
	tween:Play()
	return tween
end

function ConsoleController:_isPlayerAllowedToInteract(player: Player): boolean
	if self._state ~= "Offline" then
		return false
	end

	local character = player.Character
	if not character then
		return false
	end

	local root = character:FindFirstChild("HumanoidRootPart")
	if not root or not root:IsA("BasePart") then
		return false
	end

	local maxDistance = self._config.Interaction.MaxDistance + self._config.Interaction.ServerGraceDistance
	if (root.Position - self._interactionTarget.Position).Magnitude > maxDistance then
		return false
	end

	-- Validate a clear path from the character to the console. The client also
	-- raycasts from its camera to enforce the "look at it" part of the UX.
	local head = character:FindFirstChild("Head")
	local origin = if head and head:IsA("BasePart") then head.Position else root.Position
	local direction = self._interactionTarget.Position - origin
	if direction.Magnitude <= 0.01 then
		return true
	end

	local raycastParams = RaycastParams.new()
	raycastParams.FilterType = Enum.RaycastFilterType.Exclude
	raycastParams.FilterDescendantsInstances = { character }
	raycastParams.IgnoreWater = true

	local result = Workspace:Raycast(origin, direction, raycastParams)
	if result and not result.Instance:IsDescendantOf(self._model) then
		return false
	end

	return true
end

function ConsoleController:_clearHold(player: Player)
	self._holds[player] = nil
	if self._holdOwner == player then
		self._holdOwner = nil
	end
end

function ConsoleController:_denyHold(player: Player, reason: string)
	self:_clearHold(player)
	self._interactionEvent:FireClient(player, "HoldDenied", reason)
end

function ConsoleController:_startPowerSequence(owner: Player)
	self:_setState("Booting")

	local startAt = Workspace:GetServerTimeNow() + self._config.Cinematic.StartLeadTime
	self._model:SetAttribute("BootStartedAt", startAt)
	self._model:SetAttribute("BlackoutAt", startAt + self._config.Cinematic.BlackoutAt)
	self._cinematicEvent:FireClient(owner, "Start", startAt)
	self._interactionEvent:FireClient(owner, "BootAccepted")

	task.spawn(function()
		local remaining = startAt - Workspace:GetServerTimeNow()
		if remaining > 0 then
			task.wait(remaining)
		end

		if self._state ~= "Booting" then
			return
		end

		if self._bootSound and self._bootSound.SoundId ~= "" then
			self._bootSound:Play()
		end

		-- Open the shell just enough to expose the blue core, then settle it.
		local leftHome = self._homePanels[self._leftPanel]
		local rightHome = self._homePanels[self._rightPanel]
		if leftHome and rightHome then
			self:_tween(
				self._leftPanel,
				0.72,
				{ CFrame = leftHome * CFrame.new(-0.22, 0.03, 0) * CFrame.Angles(0, 0, math.rad(4)) }
			)
			self:_tween(
				self._rightPanel,
				0.72,
				{ CFrame = rightHome * CFrame.new(0.22, 0.03, 0) * CFrame.Angles(0, 0, math.rad(-4)) }
			)
		end

		task.wait(0.20)
		self:_tween(self._led, 0.28, { Color = START_COLOR })
		self:_tween(self._powerGlow, 0.35, { Brightness = 1.1, Range = 8 })

		task.wait(0.75)
		self:_tween(self._led, 0.85, { Color = ACTIVE_COLOR })
		self:_tween(self._powerGlow, 0.85, { Brightness = 2.7, Range = 15 })

		task.wait(0.90)
		-- A quick pulse makes the boot feel responsive even with no external SFX.
		self:_tween(self._powerGlow, 0.20, { Brightness = 4.2, Range = 19 })
		task.wait(0.22)
		self:_tween(self._powerGlow, 0.48, { Brightness = 2.35, Range = 14 })

		task.wait(1.10)
		if leftHome and rightHome then
			self:_tween(self._leftPanel, 0.90, { CFrame = leftHome * CFrame.new(-0.07, 0, 0) })
			self:_tween(self._rightPanel, 0.90, { CFrame = rightHome * CFrame.new(0.07, 0, 0) })
		end

		task.wait(0.80)
		if self._state == "Booting" then
			self:_setState("Online")
		end
	end)
end

function ConsoleController:_onInteractionRequest(player: Player, action: unknown)
	if type(action) ~= "string" then
		return
	end

	if action == "Begin" then
		if self._holdOwner and self._holdOwner ~= player then
			self._interactionEvent:FireClient(player, "HoldDenied", "ConsoleBusy")
			return
		end

		if not self:_isPlayerAllowedToInteract(player) then
			self:_denyHold(player, "OutOfRange")
			return
		end

		self._holdOwner = player
		self._holds[player] = { startedAt = Workspace:GetServerTimeNow() }
		self._interactionEvent:FireClient(player, "HoldAccepted")

		-- Do not let an abandoned Begin request reserve the console forever.
		task.delay(self._config.Interaction.HoldDuration + 1, function()
			local record = self._holds[player]
			if record and Workspace:GetServerTimeNow() - record.startedAt >= self._config.Interaction.HoldDuration + 1 then
				self:_clearHold(player)
			end
		end)
		return
	end

	if action == "Cancel" then
		self:_clearHold(player)
		return
	end

	if action ~= "Complete" then
		return
	end

	local record = self._holds[player]
	if not record or self._holdOwner ~= player then
		self:_denyHold(player, "NoActiveHold")
		return
	end

	local heldFor = Workspace:GetServerTimeNow() - record.startedAt
	if heldFor < self._config.Interaction.HoldDuration - self._config.Interaction.HoldLeeway then
		self:_denyHold(player, "HoldTooShort")
		return
	end

	if not self:_isPlayerAllowedToInteract(player) then
		self:_denyHold(player, "OutOfRange")
		return
	end

	self:_clearHold(player)
	self:_startPowerSequence(player)
end

function ConsoleController:Start()
	-- Every fresh server boot starts from a deterministic powered-off state.
	self:_setOfflineVisuals()
	self._model:SetAttribute("BootStartedAt", 0)
	self._model:SetAttribute("BlackoutAt", 0)
	self:_setState("Offline")

	table.insert(self.connections, self._interactionEvent.OnServerEvent:Connect(function(player, action)
		self:_onInteractionRequest(player, action)
	end))

	table.insert(self.connections, Players.PlayerRemoving:Connect(function(player)
		self:_clearHold(player)
	end))
end

function ConsoleController:Destroy()
	for _, connection in self.connections do
		connection:Disconnect()
	end
	table.clear(self.connections)
end

return ConsoleController
