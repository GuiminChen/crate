"use strict";
const { execFile } = require("child_process");
const {
  App,
  FileSystemAdapter,
  Notice,
  Plugin,
  PluginSettingTab,
  Setting,
  TFile,
} = require("obsidian");

const DEFAULT_EXE = "crate";

class CrateVaultPlugin extends Plugin {
  async onload() {
    await this.loadSettings();
    this.addSettingTab(new CrateSettingTab(this.app, this));
    this.addCommand({
      id: "crate-open-wiki-index",
      name: "Open wiki/_index/INDEX.md",
      callback: () => {
        void this.openVaultRelative("wiki/_index/INDEX.md");
      },
    });
    this.addCommand({
      id: "crate-open-wiki-index-json",
      name: "Open meta/wiki_index.json",
      callback: () => {
        void this.openVaultRelative("meta/wiki_index.json");
      },
    });
    this.addCommand({
      id: "crate-doctor",
      name: "Run crate doctor (terminal)",
      callback: () => {
        this.runCrateDoctor();
      },
    });
  }

  async openVaultRelative(rel) {
    const f = this.app.vault.getAbstractFileByPath(rel);
    if (!f || !(f instanceof TFile)) {
      new Notice(`CRATE: missing ${rel} (run crate init / compile first)`);
      return;
    }
    await this.app.workspace.getLeaf(false).openFile(f);
  }

  vaultRootPath() {
    const a = this.app.vault.adapter;
    if (a instanceof FileSystemAdapter) {
      return a.getBasePath();
    }
    return undefined;
  }

  runCrateDoctor() {
    const cwd = this.vaultRootPath();
    if (!cwd) {
      new Notice("CRATE: vault path unavailable (desktop vault only)");
      return;
    }
    const exe = (this.settings.crateExecutable || "").trim() || DEFAULT_EXE;
    execFile(
      exe,
      ["doctor"],
      { cwd: cwd, timeout: 120000 },
      (err, stdout, stderr) => {
        const text = (stdout || stderr || "").trim();
        if (err) {
          const msg = (stderr || err.message || "").slice(0, 400);
          new Notice(`crate doctor failed: ${msg}`, 12000);
          return;
        }
        new Notice(text.slice(0, 500) || "crate doctor ok", 12000);
      }
    );
  }

  async loadSettings() {
    this.settings = Object.assign(
      { crateExecutable: DEFAULT_EXE },
      await this.loadData()
    );
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}

class CrateSettingTab extends PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display() {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "CRATE" });
    new Setting(containerEl)
      .setName("crate executable")
      .setDesc("Command on PATH or absolute path to the crate CLI")
      .addText((tc) =>
        tc
          .setValue(this.plugin.settings.crateExecutable)
          .onChange(async (v) => {
            this.plugin.settings.crateExecutable = v || DEFAULT_EXE;
            await this.plugin.saveSettings();
          })
      );
  }
}

module.exports = CrateVaultPlugin;
