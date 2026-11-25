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
	"Установить или обновить PS5 Boot Experience в текущем place",
	""
)
installButton.ClickableWhenViewportHidden = true

-- __PS5_BOOT_SOURCES__

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
	warn("[PS5 Boot] Установка завершена. Нажмите Play, чтобы создать консоль.")
end

installButton.Click:Connect(function()
	installButton:SetActive(true)
	local success, result = pcall(installOrUpdate)
	installButton:SetActive(false)

	if not success then
		warn("[PS5 Boot] Не удалось установить опыт: " .. tostring(result))
	end
end)
