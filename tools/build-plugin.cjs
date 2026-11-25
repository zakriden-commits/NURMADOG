#!/usr/bin/env node
/*
 * Builds plugin/PS5BootInstaller.rbxm from the maintained source files.
 *
 * One-time dependency:
 *   npm install --no-save rbxm-parser
 *
 * The generated binary is round-tripped immediately so CI/manual use can
 * catch a corrupt file before it is shared with Studio users.
 */

const fs = require("fs");
const path = require("path");
const { RobloxFile, RunContext, Script } = require("rbxm-parser");

const root = path.resolve(__dirname, "..");
const sourceFiles = {
	ConsoleConfig: "src/shared/ConsoleConfig.lua",
	ConsoleBuilder: "src/server/Console/ConsoleBuilder.lua",
	ConsoleController: "src/server/Console/ConsoleController.lua",
	Bootstrap: "src/server/Bootstrap.server.lua",
	ConsoleClient: "src/client/ConsoleClient.client.lua",
};

function read(relativePath) {
	return fs.readFileSync(path.join(root, relativePath), "utf8").replace(/\r\n/g, "\n");
}

function asLongString(source) {
	let equals = "";
	while (source.includes(`]${equals}]`)) {
		equals += "=";
	}
	return `[${equals}[${source}]${equals}]`;
}

function createSourceTable() {
	const entries = Object.entries(sourceFiles)
		.map(([name, file]) => `\t${name} = ${asLongString(read(file))},`)
		.join("\n");
	return `local SOURCES = {\n${entries}\n}\n`;
}

// rbxm-parser writes string properties through a legacy byte path. Keeping the
// plugin payload ASCII avoids corrupting Cyrillic UI text in the binary file.
// The emitted Luau unicode escapes are interpreted when the installer writes
// the source into Studio, so the in-game Russian text remains intact.
function escapeNonAsciiForLuau(source) {
	return source.replace(/[^\x00-\x7F]/gu, (character) => {
		const codePoint = character.codePointAt(0);
		return `\\u{${codePoint.toString(16).toUpperCase()}}`;
	});
}

const templatePath = path.join(root, "plugin/PS5BootInstaller.template.lua");
const pluginLuaPath = path.join(root, "plugin/PS5BootInstaller.plugin.lua");
const pluginRbxmPath = path.join(root, "plugin/PS5BootInstaller.rbxm");
const marker = "-- __PS5_BOOT_SOURCES__";
const template = read("plugin/PS5BootInstaller.template.lua");

if ((template.match(new RegExp(marker, "g")) || []).length !== 1) {
	throw new Error(`Expected exactly one ${marker} marker in ${templatePath}`);
}

const pluginSource = escapeNonAsciiForLuau(template.replace(marker, createSourceTable()));
fs.writeFileSync(pluginLuaPath, pluginSource, "utf8");

const pluginScript = new Script();
pluginScript.Name = "PS5BootInstaller";
pluginScript.RunContext = RunContext.Plugin;
pluginScript.Disabled = false;
pluginScript.Source = pluginSource;

const file = new RobloxFile();
file.Metadata.set("Creator", "NURMADOG");
file.Metadata.set("Summary", "Local installer for PS5 Boot Experience");
file.AddRoot(pluginScript);
fs.writeFileSync(pluginRbxmPath, file.WriteToBuffer());

const verified = RobloxFile.ReadFromBuffer(fs.readFileSync(pluginRbxmPath));
if (!verified || verified.Roots.length !== 1) {
	throw new Error("Generated plugin could not be read back as a one-root Roblox model");
}

const verifiedScript = verified.Roots[0];
if (
	verifiedScript.ClassName !== "Script" ||
	verifiedScript.Name !== "PS5BootInstaller" ||
	verifiedScript.Source !== pluginSource
) {
	throw new Error("Generated plugin round-trip verification failed");
}

console.log(`Built and verified ${path.relative(root, pluginRbxmPath)}`);
