--!strict

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
