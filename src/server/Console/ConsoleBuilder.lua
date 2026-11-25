--!strict

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
