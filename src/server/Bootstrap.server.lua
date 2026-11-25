--!strict

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
