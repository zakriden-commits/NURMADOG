--!nonstrict
-- PS5 Boot Experience local Studio plugin.
-- This file is generated from the maintained Luau sources in ../src.
-- Install the generated .rbxm as a local plugin, then click the toolbar button.

local ChangeHistoryService = game:GetService("ChangeHistoryService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Selection = game:GetService("Selection")
local ServerScriptService = game:GetService("ServerScriptService")
local StarterPlayer = game:GetService("StarterPlayer")

local toolbar = plugin:CreateToolbar("PS5 Boot")
local installButton = toolbar:CreateButton(
	"InstallPS5BootExperience",
	"\u{423}\u{441}\u{442}\u{430}\u{43D}\u{43E}\u{432}\u{438}\u{442}\u{44C} \u{438}\u{43B}\u{438} \u{43E}\u{431}\u{43D}\u{43E}\u{432}\u{438}\u{442}\u{44C} PS5 Boot Experience \u{432} \u{442}\u{435}\u{43A}\u{443}\u{449}\u{435}\u{43C} place",
	""
)
installButton.ClickableWhenViewportHidden = true

local SOURCES = {
	ConsoleConfig = [[--!strict

-- Central configuration for the PS5 boot experience.
-- Keep this module free of server/client-only services so it can be required on both sides.

export type ConsoleConfig = {
	ModelName: string,
	SpawnCFrame: CFrame,
	Interaction: {
		MaxDistance: number,
		HoldDuration: number,
		HoldLeeway: number,
		ServerGraceDistance: number,
	},
	Cinematic: {
		StartLeadTime: number,
		BlackoutAt: number,
		BlackoutPersistenceSeconds: number,
	},
	Audio: {
		-- Leave blank unless you own or have licensed a Roblox audio asset for this project.
		PowerOnSoundId: string,
		Volume: number,
	},
}

local Config: ConsoleConfig = {
	ModelName = "PS5Console",

	-- The console faces the default Roblox spawn at world origin.
	SpawnCFrame = CFrame.new(0, 0, -18) * CFrame.Angles(0, math.rad(180), 0),

	Interaction = {
		MaxDistance = 10,
		HoldDuration = 1.65,
		-- Compensates for normal client/server replication latency, not for skipping the hold.
		HoldLeeway = 0.12,
		ServerGraceDistance = 1.25,
	},

	Cinematic = {
		-- Gives the client enough time to place the camera behind a black fade.
		StartLeadTime = 0.45,
		-- Camera sequence is synchronized to this timestamp and fades to black here.
		BlackoutAt = 6.35,
		-- 0 keeps the requested final blackout on screen. Set e.g. 2.5 to return to gameplay.
		BlackoutPersistenceSeconds = 0,
	},

	Audio = {
		PowerOnSoundId = "",
		Volume = 0.55,
	},
}

return table.freeze(Config)
]],
	ConsoleBuilder = [[--!strict

-- Builds an original, PS5-inspired console from Roblox primitives at runtime.
-- No marketplace model, mesh, texture, or unlicensed Sony asset is required.

local ConsoleBuilder = {}

local EXPERIENCE_ATTRIBUTE = "PS5BootExperience"

type AudioConfig = {
	PowerOnSoundId: string,
	Volume: number,
}

type BuilderConfig = {
	ModelName: string,
	SpawnCFrame: CFrame,
	Audio: AudioConfig,
}

type PartOptions = {
	Color: Color3?,
	Material: Enum.Material?,
	Transparency: number?,
	CanCollide: boolean?,
	CanQuery: boolean?,
	CanTouch: boolean?,
	CastShadow: boolean?,
	Reflectance: number?,
	Shape: Enum.PartType?,
}

local COLORS = {
	Shell = Color3.fromRGB(239, 242, 247),
	ShellShadow = Color3.fromRGB(193, 201, 211),
	Core = Color3.fromRGB(8, 11, 17),
	CoreEdge = Color3.fromRGB(20, 27, 39),
	Metal = Color3.fromRGB(31, 38, 49),
	MetalDark = Color3.fromRGB(13, 18, 25),
	BlueOff = Color3.fromRGB(3, 16, 33),
	BlueOn = Color3.fromRGB(72, 183, 255),
}

local function makeFolder(parent: Instance, name: string): Folder
	local folder = Instance.new("Folder")
	folder.Name = name
	folder.Parent = parent
	return folder
end

local function makePart(
	parent: Instance,
	name: string,
	size: Vector3,
	worldCFrame: CFrame,
	options: PartOptions?
): Part
	local part = Instance.new("Part")
	part.Name = name
	part.Size = size
	part.CFrame = worldCFrame
	part.Anchored = true
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	part.Color = if options and options.Color then options.Color else COLORS.Core
	part.Material = if options and options.Material then options.Material else Enum.Material.SmoothPlastic
	part.Transparency = if options and options.Transparency then options.Transparency else 0
	part.CanCollide = if options and options.CanCollide ~= nil then options.CanCollide else false
	part.CanQuery = if options and options.CanQuery ~= nil then options.CanQuery else true
	part.CanTouch = if options and options.CanTouch ~= nil then options.CanTouch else false
	part.CastShadow = if options and options.CastShadow ~= nil then options.CastShadow else true
	part.Reflectance = if options and options.Reflectance then options.Reflectance else 0

	if options and options.Shape then
		part.Shape = options.Shape
	end

	part.Parent = parent
	return part
end

local function makeWedge(
	parent: Instance,
	name: string,
	size: Vector3,
	worldCFrame: CFrame,
	color: Color3
): WedgePart
	local wedge = Instance.new("WedgePart")
	wedge.Name = name
	wedge.Size = size
	wedge.CFrame = worldCFrame
	wedge.Anchored = true
	wedge.TopSurface = Enum.SurfaceType.Smooth
	wedge.BottomSurface = Enum.SurfaceType.Smooth
	wedge.Color = color
	wedge.Material = Enum.Material.SmoothPlastic
	wedge.CanCollide = false
	wedge.CanTouch = false
	wedge.CanQuery = true
	wedge.Parent = parent
	return wedge
end

local function world(base: CFrame, localCFrame: CFrame): CFrame
	return base * localCFrame
end

local function addCylinder(
	parent: Instance,
	name: string,
	size: Vector3,
	base: CFrame,
	localCFrame: CFrame,
	color: Color3,
	material: Enum.Material
): Part
	return makePart(parent, name, size, world(base, localCFrame), {
		Color = color,
		Material = material,
		Shape = Enum.PartType.Cylinder,
	})
end

local function makePanelDetails(visuals: Folder, base: CFrame)
	-- Narrow graphite insets provide depth between the white shell and black core.
	for index = 0, 8 do
		local y = 1.34 + index * 0.48
		for _, side in { -1, 1 } do
			makePart(
				visuals,
				string.format("Vent_%d_%d", side, index),
				Vector3.new(0.32, 0.055, 0.11),
				world(base, CFrame.new(side * 0.72, y, -1.43)),
				{
					Color = COLORS.MetalDark,
					Material = Enum.Material.Metal,
					CastShadow = false,
				}
			)
		end
	end

	-- Subtle blue trim only becomes emissive when the controller powers on.
	for index = 1, 4 do
		makePart(
			visuals,
			"CoreRidge_" .. index,
			Vector3.new(0.025, 0.72, 0.03),
			world(base, CFrame.new(-0.31 + index * 0.16, 1.35 + index * 0.88, -1.47)),
			{
				Color = COLORS.CoreEdge,
				Material = Enum.Material.Metal,
				CastShadow = false,
			}
		)
	end
end

function ConsoleBuilder.findExisting(parent: Instance): Model?
	for _, child in parent:GetChildren() do
		if child:IsA("Model") and child:GetAttribute(EXPERIENCE_ATTRIBUTE) == true then
			return child
		end
	end

	return nil
end

function ConsoleBuilder.build(parent: Instance, config: BuilderConfig): Model
	local base = config.SpawnCFrame
	local model = Instance.new("Model")
	model.Name = config.ModelName
	model:SetAttribute(EXPERIENCE_ATTRIBUTE, true)
	model:SetAttribute("ConsoleState", "Offline")
	model:SetAttribute("BootStartedAt", 0)
	model:SetAttribute("BlackoutAt", 0)
	model.Parent = parent

	local root = makePart(model, "Root", Vector3.new(0.2, 0.2, 0.2), base, {
		Transparency = 1,
		CanCollide = false,
		CanQuery = false,
		CanTouch = false,
		CastShadow = false,
	})
	model.PrimaryPart = root

	local visuals = makeFolder(model, "Visuals")
	local effects = makeFolder(model, "Effects")

	-- Display pedestal --------------------------------------------------------
	addCylinder(
		visuals,
		"PedestalShadow",
		Vector3.new(0.18, 5.2, 5.2),
		base,
		CFrame.new(0, 0.09, 0) * CFrame.Angles(0, 0, math.rad(90)),
		COLORS.MetalDark,
		Enum.Material.Metal
	)
	addCylinder(
		visuals,
		"PedestalRing",
		Vector3.new(0.14, 4.64, 4.64),
		base,
		CFrame.new(0, 0.18, 0) * CFrame.Angles(0, 0, math.rad(90)),
		COLORS.Metal,
		Enum.Material.Metal
	)
	addCylinder(
		visuals,
		"PedestalTop",
		Vector3.new(0.12, 4.16, 4.16),
		base,
		CFrame.new(0, 0.28, 0) * CFrame.Angles(0, 0, math.rad(90)),
		COLORS.Core,
		Enum.Material.SmoothPlastic
	)

	-- The dark central body. White shell pieces sit slightly away from it.
	makePart(visuals, "Core", Vector3.new(1.48, 5.72, 2.66), world(base, CFrame.new(0, 3.08, 0)), {
		Color = COLORS.Core,
		Material = Enum.Material.SmoothPlastic,
		Reflectance = 0.04,
		CanCollide = true,
	})
	makePart(
		visuals,
		"CoreFront",
		Vector3.new(1.30, 5.14, 0.10),
		world(base, CFrame.new(0, 3.05, -1.385)),
		{
			Color = Color3.fromRGB(5, 8, 13),
			Material = Enum.Material.Glass,
			Reflectance = 0.07,
		}
	)
	makePart(
		visuals,
		"CoreTop",
		Vector3.new(1.22, 0.12, 2.38),
		world(base, CFrame.new(0, 5.98, 0)),
		{
			Color = COLORS.CoreEdge,
			Material = Enum.Material.Metal,
			CastShadow = false,
		}
	)

	-- White outer shell. These two parts are the animated panels used by the boot sequence.
	local leftPanel = makePart(
		visuals,
		"PanelLeft",
		Vector3.new(0.24, 5.86, 3.34),
		world(base, CFrame.new(-0.99, 3.14, 0) * CFrame.Angles(0, 0, math.rad(5.5))),
		{
			Color = COLORS.Shell,
			Material = Enum.Material.SmoothPlastic,
			Reflectance = 0.02,
			CanCollide = true,
		}
	)
	leftPanel:SetAttribute("AnimatedPanel", true)

	local rightPanel = makePart(
		visuals,
		"PanelRight",
		Vector3.new(0.24, 5.86, 3.34),
		world(base, CFrame.new(0.99, 3.14, 0) * CFrame.Angles(0, 0, math.rad(-5.5))),
		{
			Color = COLORS.Shell,
			Material = Enum.Material.SmoothPlastic,
			Reflectance = 0.02,
			CanCollide = true,
		}
	)
	rightPanel:SetAttribute("AnimatedPanel", true)

	-- Angular caps soften the silhouette without relying on an imported mesh.
	makeWedge(
		visuals,
		"LeftUpperWing",
		Vector3.new(0.26, 1.00, 3.42),
		world(base, CFrame.new(-1.04, 6.00, 0) * CFrame.Angles(0, 0, math.rad(95.5))),
		COLORS.Shell
	)
	makeWedge(
		visuals,
		"RightUpperWing",
		Vector3.new(0.26, 1.00, 3.42),
		world(base, CFrame.new(1.04, 6.00, 0) * CFrame.Angles(0, math.rad(180), math.rad(-95.5))),
		COLORS.Shell
	)
	makePart(
		visuals,
		"LeftPanelShadow",
		Vector3.new(0.05, 5.28, 2.86),
		world(base, CFrame.new(-0.80, 3.08, 0) * CFrame.Angles(0, 0, math.rad(5.5))),
		{
			Color = COLORS.ShellShadow,
			Material = Enum.Material.SmoothPlastic,
			CastShadow = false,
		}
	)
	makePart(
		visuals,
		"RightPanelShadow",
		Vector3.new(0.05, 5.28, 2.86),
		world(base, CFrame.new(0.80, 3.08, 0) * CFrame.Angles(0, 0, math.rad(-5.5))),
		{
			Color = COLORS.ShellShadow,
			Material = Enum.Material.SmoothPlastic,
			CastShadow = false,
		}
	)

	-- Front details -----------------------------------------------------------
	makePart(
		visuals,
		"DiscSlot",
		Vector3.new(0.50, 0.045, 0.055),
		world(base, CFrame.new(0.34, 2.20, -1.47)),
		{
			Color = Color3.fromRGB(0, 0, 0),
			Material = Enum.Material.Metal,
			CastShadow = false,
		}
	)
	makePart(
		visuals,
		"UsbPort",
		Vector3.new(0.22, 0.12, 0.06),
		world(base, CFrame.new(-0.28, 1.72, -1.47)),
		{
			Color = Color3.fromRGB(1, 2, 4),
			Material = Enum.Material.Metal,
			CastShadow = false,
		}
	)
	makePart(
		visuals,
		"PowerButton",
		Vector3.new(0.18, 0.18, 0.07),
		world(base, CFrame.new(0.02, 1.29, -1.48)),
		{
			Color = COLORS.Metal,
			Material = Enum.Material.Metal,
			CastShadow = false,
		}
	)

	local led = makePart(
		visuals,
		"PowerLed",
		Vector3.new(0.048, 2.16, 0.055),
		world(base, CFrame.new(0, 3.31, -1.49)),
		{
			Color = COLORS.BlueOff,
			Material = Enum.Material.Neon,
			CastShadow = false,
		}
	)
	led:SetAttribute("OfflineColor", COLORS.BlueOff)
	led:SetAttribute("OnlineColor", COLORS.BlueOn)

	local light = Instance.new("PointLight")
	light.Name = "PowerGlow"
	light.Color = COLORS.BlueOn
	light.Brightness = 0
	light.Range = 0
	light.Shadows = false
	light.Parent = led

	makePanelDetails(visuals, base)

	-- A client raycast can only select this hitbox or actual console geometry.
	local interactionTarget = makePart(
		model,
		"InteractionTarget",
		Vector3.new(4.4, 6.6, 0.65),
		world(base, CFrame.new(0, 3.18, -1.98)),
		{
			Transparency = 1,
			CanCollide = false,
			CanQuery = true,
			CanTouch = false,
			CastShadow = false,
		}
	)
	interactionTarget:SetAttribute("InteractionTarget", true)

	local focus = Instance.new("Attachment")
	focus.Name = "CinematicFocus"
	focus.Position = Vector3.new(0, 3.15, -0.55)
	focus.Parent = root

	if config.Audio.PowerOnSoundId ~= "" then
		local bootSound = Instance.new("Sound")
		bootSound.Name = "PowerOnSfx"
		bootSound.SoundId = config.Audio.PowerOnSoundId
		bootSound.Volume = config.Audio.Volume
		bootSound.RollOffMode = Enum.RollOffMode.InverseTapered
		bootSound.RollOffMinDistance = 4
		bootSound.RollOffMaxDistance = 35
		bootSound.Parent = root
	end

	return model
end

return ConsoleBuilder
]],
	ConsoleController = [[--!strict

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
]],
	Bootstrap = [[--!strict

-- Entry point. Rojo places this Script in ServerScriptService/PS5BootExperience.

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")

local shared = ReplicatedStorage:WaitForChild("PS5BootShared")
local Config = require(shared:WaitForChild("ConsoleConfig"))

local consoleFolder = script.Parent:WaitForChild("Console")
local ConsoleBuilder = require(consoleFolder:WaitForChild("ConsoleBuilder"))
local ConsoleController = require(consoleFolder:WaitForChild("ConsoleController"))

local function getOrCreateFolder(parent: Instance, name: string): Folder
	local existing = parent:FindFirstChild(name)
	if existing then
		assert(existing:IsA("Folder"), string.format("%s.%s must be a Folder", parent:GetFullName(), name))
		return existing
	end

	local folder = Instance.new("Folder")
	folder.Name = name
	folder.Parent = parent
	return folder
end

local function getOrCreateRemote(parent: Instance, name: string): RemoteEvent
	local existing = parent:FindFirstChild(name)
	if existing then
		assert(existing:IsA("RemoteEvent"), string.format("%s.%s must be a RemoteEvent", parent:GetFullName(), name))
		return existing
	end

	local remote = Instance.new("RemoteEvent")
	remote.Name = name
	remote.Parent = parent
	return remote
end

local function getOrCreateModelReference(parent: Instance): ObjectValue
	local existing = parent:FindFirstChild("ConsoleModel")
	if existing then
		assert(existing:IsA("ObjectValue"), string.format("%s.ConsoleModel must be an ObjectValue", parent:GetFullName()))
		return existing
	end

	local reference = Instance.new("ObjectValue")
	reference.Name = "ConsoleModel"
	reference.Parent = parent
	return reference
end

local remotes = getOrCreateFolder(ReplicatedStorage, "PS5BootRemotes")
local interactionEvent = getOrCreateRemote(remotes, "Interaction")
local cinematicEvent = getOrCreateRemote(remotes, "Cinematic")
local modelReference = getOrCreateModelReference(remotes)

local console = ConsoleBuilder.findExisting(Workspace)
if not console then
	console = ConsoleBuilder.build(Workspace, Config)
end
modelReference.Value = console

local controller = ConsoleController.new(console, Config, interactionEvent, cinematicEvent)
controller:Start()

script.Destroying:Connect(function()
	controller:Destroy()
end)
]],
	ConsoleClient = [[--!strict

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
promptSubTitle.Text = "\u{41A}\u{41E}\u{41D}\u{421}\u{41E}\u{41B}\u{42C} \u{41E}\u{416}\u{418}\u{414}\u{410}\u{415}\u{422} \u{417}\u{410}\u{41F}\u{423}\u{421}\u{41A}\u{410}"
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
instruction.Text = "\u{423}\u{414}\u{415}\u{420}\u{416}\u{418}\u{412}\u{410}\u{419}\u{422}\u{415}, \u{427}\u{422}\u{41E}\u{411}\u{42B} \u{412}\u{41A}\u{41B}\u{42E}\u{427}\u{418}\u{422}\u{42C}"
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
statusLabel.Text = "\u{413}\u{41E}\u{422}\u{41E}\u{412}\u{41E}"
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
	instruction.Text = "\u{423}\u{414}\u{415}\u{420}\u{416}\u{418}\u{412}\u{410}\u{419}\u{422}\u{415}, \u{427}\u{422}\u{41E}\u{411}\u{42B} \u{412}\u{41A}\u{41B}\u{42E}\u{427}\u{418}\u{422}\u{42C}"
	statusLabel.Text = "\u{413}\u{41E}\u{422}\u{41E}\u{412}\u{41E}"
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

	instruction.Text = "\u{41D}\u{415} \u{41E}\u{422}\u{41F}\u{423}\u{421}\u{41A}\u{410}\u{419}\u{422}\u{415} \u{41A}\u{41B}\u{410}\u{412}\u{418}\u{428}\u{423}"
	statusLabel.Text = "\u{41F}\u{420}\u{41E}\u{412}\u{415}\u{420}\u{41A}\u{410} \u{41F}\u{418}\u{422}\u{410}\u{41D}\u{418}\u{42F}"
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
		instruction.Text = "\u{421}\u{418}\u{413}\u{41D}\u{410}\u{41B} \u{41F}\u{420}\u{418}\u{41D}\u{42F}\u{422}"
		statusLabel.Text = "\u{417}\u{410}\u{41F}\u{423}\u{421}\u{41A}"
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
	showCaption("\u{412}\u{41A}\u{41B}\u{42E}\u{427}\u{415}\u{41D}\u{418}\u{415} \u{421}\u{418}\u{421}\u{422}\u{415}\u{41C}\u{42B}")
	tween(fade, 0.55, { BackgroundTransparency = 0.12 }, Enum.EasingStyle.Quad)
	tween(camera, 1.72, { CFrame = front, FieldOfView = 49 }, Enum.EasingStyle.Quart)

	waitForOffset(startAt, 1.72)
	showCaption("\u{41F}\u{418}\u{422}\u{410}\u{41D}\u{418}\u{415} \u{41F}\u{41E}\u{414}\u{410}\u{41D}\u{41E}")
	tween(camera, 1.62, { CFrame = detail, FieldOfView = 43 }, Enum.EasingStyle.Quart)

	waitForOffset(startAt, 3.34)
	showCaption("\u{418}\u{41D}\u{418}\u{426}\u{418}\u{410}\u{41B}\u{418}\u{417}\u{410}\u{426}\u{418}\u{42F} \u{42F}\u{414}\u{420}\u{410}")
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
]],
}


local INSTALL_ATTRIBUTE = "PS5BootExperience"

local function ensureFolder(parent, name)
	local existing = parent:FindFirstChild(name)
	if existing and existing:IsA("Folder") then
		return existing
	end

	if existing then
		existing:Destroy()
	end

	local folder = Instance.new("Folder")
	folder.Name = name
	folder.Parent = parent
	return folder
end

local function upsertSource(parent, className, name, source)
	local existing = parent:FindFirstChild(name)
	if existing and existing.ClassName ~= className then
		existing:Destroy()
		existing = nil
	end

	local container = existing or Instance.new(className)
	container.Name = name
	container.Source = source
	container:SetAttribute(INSTALL_ATTRIBUTE, true)
	container.Parent = parent
	return container
end

local function installOrUpdate()
	ChangeHistoryService:SetWaypoint("Before PS5 Boot Experience install")

	-- This hierarchy is deliberately namespaced. Existing game content outside
	-- these nodes is never replaced by the plugin.
	local shared = ensureFolder(ReplicatedStorage, "PS5BootShared")
	shared:SetAttribute(INSTALL_ATTRIBUTE, true)
	upsertSource(shared, "ModuleScript", "ConsoleConfig", SOURCES.ConsoleConfig)

	local serverRoot = ensureFolder(ServerScriptService, "PS5BootExperience")
	serverRoot:SetAttribute(INSTALL_ATTRIBUTE, true)
	local consoleFolder = ensureFolder(serverRoot, "Console")
	consoleFolder:SetAttribute(INSTALL_ATTRIBUTE, true)
	upsertSource(consoleFolder, "ModuleScript", "ConsoleBuilder", SOURCES.ConsoleBuilder)
	upsertSource(consoleFolder, "ModuleScript", "ConsoleController", SOURCES.ConsoleController)
	upsertSource(serverRoot, "Script", "Bootstrap", SOURCES.Bootstrap)

	local starterPlayerScripts = StarterPlayer:WaitForChild("StarterPlayerScripts")
	local clientRoot = ensureFolder(starterPlayerScripts, "PS5BootExperience")
	clientRoot:SetAttribute(INSTALL_ATTRIBUTE, true)
	upsertSource(clientRoot, "LocalScript", "ConsoleClient", SOURCES.ConsoleClient)

	Selection:Set({ serverRoot })
	ChangeHistoryService:SetWaypoint("Install PS5 Boot Experience")
	warn("[PS5 Boot] \u{423}\u{441}\u{442}\u{430}\u{43D}\u{43E}\u{432}\u{43A}\u{430} \u{437}\u{430}\u{432}\u{435}\u{440}\u{448}\u{435}\u{43D}\u{430}. \u{41D}\u{430}\u{436}\u{43C}\u{438}\u{442}\u{435} Play, \u{447}\u{442}\u{43E}\u{431}\u{44B} \u{441}\u{43E}\u{437}\u{434}\u{430}\u{442}\u{44C} \u{43A}\u{43E}\u{43D}\u{441}\u{43E}\u{43B}\u{44C}.")
end

installButton.Click:Connect(function()
	installButton:SetActive(true)
	local success, result = pcall(installOrUpdate)
	installButton:SetActive(false)

	if not success then
		warn("[PS5 Boot] \u{41D}\u{435} \u{443}\u{434}\u{430}\u{43B}\u{43E}\u{441}\u{44C} \u{443}\u{441}\u{442}\u{430}\u{43D}\u{43E}\u{432}\u{438}\u{442}\u{44C} \u{43E}\u{43F}\u{44B}\u{442}: " .. tostring(result))
	end
end)
