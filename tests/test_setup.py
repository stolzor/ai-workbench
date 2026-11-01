import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="setup spaces '")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "repo space"
        (self.repo / "bin").mkdir(parents=True)
        (self.repo / "config").mkdir()
        shutil.copyfile(SOURCE / "bin/setup", self.repo / "bin/setup")
        for name in ("opencode", "oh-my-opencode-slim"):
            (self.repo / "config" / (name + ".jsonc")).write_text("{}")
        self.home = self.base / "home space"
        self.home.mkdir()
        self.tools = self.base / "tools space"
        self.tools.mkdir()
        mise = self.tools / "mise"
        mise.write_text("#!/bin/sh\nprintf 'export SETUP_ACTIVATED=yes\\n'\n")
        mise.chmod(0o755)
        uname = self.tools / "uname"
        uname.write_text("#!/bin/sh\nprintf '%s\\n' Linux\n")
        uname.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), SHELL="/bin/bash",
                        PATH=str(self.tools) + os.pathsep + os.environ["PATH"])
        self.env.pop("XDG_CONFIG_HOME", None)
        self.env.pop("ZDOTDIR", None)
        self.config = self.home / ".config/opencode"

    def run_setup(self):
        return subprocess.run(["sh", str(self.repo / "bin/setup")], env=self.env,
                              text=True, capture_output=True, check=True)

    def test_fresh_repeat_and_quoted_activation(self):
        result = self.run_setup()
        rc = self.home / ".bashrc"
        original = rc.read_text()
        self.assertIn("Launch the repository wrapper:", result.stdout)
        for name in ("opencode", "oh-my-opencode-slim"):
            link = self.config / (name + ".jsonc")
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.readlink(), self.repo / "config" / (name + ".jsonc"))
        self.run_setup()
        self.assertEqual(rc.read_text(), original)
        self.assertFalse(list(self.config.glob("*.bak.*")))
        result = subprocess.run(["sh", "-c", '. "$HOME/.bashrc"; printf "%s" "$SETUP_ACTIVATED"'],
                                env=self.env, text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout, "yes")

    def test_conflicts_and_backup_collision(self):
        self.config.mkdir(parents=True)
        (self.config / "opencode.json").write_text("legacy")
        (self.config / "opencode.jsonc").mkdir()
        (self.config / "opencode.jsonc/keep").write_text("directory")
        (self.config / "oh-my-opencode-slim.json").symlink_to("missing")
        (self.config / "oh-my-opencode-slim.jsonc").write_text("current")
        date = self.tools / "date"
        # Freeze the timestamp so an already existing backup must not be replaced.
        date.write_text("#!/bin/sh\nprintf '%s\\n' fixed\n")
        date.chmod(0o755)
        collision = self.config / "opencode.json.bak.fixed"
        collision.write_text("existing backup")
        self.run_setup()
        self.assertEqual(collision.read_text(), "existing backup")
        self.assertEqual((self.config / "opencode.json.bak.fixed.1").read_text(), "legacy")
        self.assertEqual((self.config / "opencode.jsonc.bak.fixed/keep").read_text(), "directory")
        self.assertTrue((self.config / "oh-my-opencode-slim.json.bak.fixed").is_symlink())
        self.assertEqual((self.config / "oh-my-opencode-slim.jsonc.bak.fixed").read_text(), "current")

    def test_fresh_zsh_activation(self):
        self.env["SHELL"] = "/bin/zsh"
        self.run_setup()
        rc = self.home / ".zshrc"
        original = rc.read_text()
        self.assertIn("activate zsh", original)
        self.run_setup()
        self.assertEqual(rc.read_text(), original)
        result = subprocess.run(["sh", "-c", '. "$HOME/.zshrc"; printf "%s" "$SETUP_ACTIVATED"'],
                                env=self.env, text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout, "yes")

    def test_commented_activation_does_not_skip_setup(self):
        self.env["SHELL"] = "/bin/zsh"
        rc = self.home / ".zshrc"
        content = '  # eval "$(mise activate zsh)"\n'
        rc.write_text(content)
        self.run_setup()
        original = rc.read_text()
        self.assertTrue(original.startswith(content))
        self.assertIn("activate zsh", original[len(content):])
        self.run_setup()
        self.assertEqual(rc.read_text(), original)
        result = subprocess.run(["sh", "-c", '. "$HOME/.zshrc"; printf "%s" "$SETUP_ACTIVATED"'],
                                env=self.env, text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout, "yes")

    def test_xdg_zdotdir_existing_activation(self):
        self.env.update(SHELL="/bin/zsh", XDG_CONFIG_HOME=str(self.base / "xdg space"),
                        ZDOTDIR=str(self.base / "zsh space"))
        rc = Path(self.env["ZDOTDIR"]) / ".zshrc"
        rc.parent.mkdir()
        content = '# keep me\neval "$(mise   activate  \'zsh\')"\n'
        rc.write_text(content)
        self.run_setup()
        self.assertEqual(rc.read_text(), content)
        self.assertTrue((Path(self.env["XDG_CONFIG_HOME"]) / "opencode/opencode.jsonc").is_symlink())
        self.assertFalse((self.home / ".bashrc").exists())

    def test_unsupported_shell(self):
        self.env["SHELL"] = "/bin/fish"
        result = self.run_setup()
        self.assertIn("not configured automatically", result.stdout)
        self.assertFalse((self.home / ".bashrc").exists())
        self.assertFalse((self.home / ".zshrc").exists())

    def test_relative_equivalent_link_is_preserved(self):
        self.run_setup()
        link = self.config / "opencode.jsonc"
        link.unlink()
        relative = os.path.relpath(self.repo / "config/opencode.jsonc", self.config)
        link.symlink_to(relative)
        self.run_setup()
        self.assertEqual(str(link.readlink()), relative)
        self.assertFalse(list(self.config.glob("*.bak.*")))

    def test_darwin_login_profile(self):
        uname = self.tools / "uname"
        uname.write_text("#!/bin/sh\nprintf '%s\\n' Darwin\n")
        uname.chmod(0o755)
        profile = self.home / ".profile"
        profile.write_text("# existing profile\n")
        self.run_setup()
        self.assertTrue(profile.read_text().startswith("# existing profile\n"))
        self.assertIn("activate bash", profile.read_text())
        self.assertFalse((self.home / ".bashrc").exists())
        self.assertFalse((self.home / ".bash_profile").exists())

    def test_empty_home_rejected(self):
        self.env["HOME"] = ""
        result = subprocess.run(["sh", str(self.repo / "bin/setup")], env=self.env,
                                capture_output=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
