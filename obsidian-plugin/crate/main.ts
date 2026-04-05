import { execFile } from "child_process";
import {
  App,
  FileSystemAdapter,
  Notice,
  Plugin,
  PluginSettingTab,
  Setting,
  TFile,
} from "obsidian";

interface CrateSettings {
  crateExecutable: string;
}

const DEFAULT_EXE = "crate";

export default class CrateVaultPlugin extends Plugin {
  settings: CrateSettings = { crateExecutable: DEFAULT_EXE };

  async onload(): Promise<void> {
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

  async openVaultRelative(rel: string): Promise<void> {
    const f = this.app.vault.getAbstractFileByPath(rel);
    if (!f || !(f instanceof TFile)) {
      new Notice(`CRATE: missing ${rel} (run crate init / compile first)`);
      return;
    }
    await this.app.workspace.getLeaf(false).openFile(f);
  }

  vaultRootPath(): string | undefined {
    const a = this.app.vault.adapter;
    if (a instanceof FileSystemAdapter) {
      return a.getBasePath();
    }
    return undefined;
  }

  runCrateDoctor(): void {
    const cwd = this.vaultRootPath();
    if (!cwd) {
      new Notice("CRATE: vault path unavailable (desktop vault only)");
      return;
    }
    const exe = this.settings.crateExecutable.trim() || DEFAULT_EXE;
    execFile(
      exe,
      ["doctor"],
      { cwd, timeout: 120_000 },
      (err, stdout, stderr) => {
        const text = (stdout || stderr || "").trim();
        if (err) {
          new Notice(
            `crate doctor failed: ${(stderr || err.message).slice(0, 400)}`,
            12000
          );
          return;
        }
        new Notice(text.slice(0, 500) || "crate doctor ok", 12000);
      }
    );
  }

  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, this.settings, await this.loadData());
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
  }
}

class CrateSettingTab extends PluginSettingTab {
  plugin: CrateVaultPlugin;

  constructor(app: App, plugin: CrateVaultPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
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
