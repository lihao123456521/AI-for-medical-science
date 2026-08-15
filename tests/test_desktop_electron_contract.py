import json
import unittest
from pathlib import Path


class DesktopElectronContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = Path(__file__).resolve().parents[1]

    def read(self, *parts):
        return (self.project.joinpath(*parts)).read_text(encoding="utf-8")

    def test_package_json_defines_electron_shell_contract(self):
        pkg = json.loads(self.read("package.json"))

        self.assertEqual(pkg["main"], "desktop/main.cjs")
        self.assertEqual(pkg["build"]["appId"], "edu.sjtu.uropuc")
        self.assertEqual(pkg["build"]["productName"], "UroPUC")
        self.assertTrue(pkg["build"]["asar"])

        targets = json.dumps(pkg["build"]["win"]["target"])
        self.assertIn("nsis", targets)

        nsis = pkg["build"]["nsis"]
        self.assertTrue(nsis["createDesktopShortcut"])
        self.assertTrue(nsis["createStartMenuShortcut"])

        extras = json.dumps(pkg["build"]["extraResources"])
        self.assertIn("backend/UroPUCBackend", extras)

        for script in ("desktop:dev", "desktop:dist", "backend:build"):
            self.assertIn(script, pkg["scripts"])

        dev_deps = pkg.get("devDependencies", {})
        self.assertIn("electron", dev_deps)
        self.assertIn("electron-builder", dev_deps)

        lock = json.loads(self.read("package-lock.json"))
        self.assertIn("electron", lock.get("packages", {}).get("", {}).get("devDependencies", {}))

    def test_main_process_security_and_lifecycle(self):
        source = self.read("desktop", "main.cjs")

        self.assertIn("app.requestSingleInstanceLock()", source)
        self.assertIn("nodeIntegration: false", source)
        self.assertIn("contextIsolation: true", source)
        self.assertIn("sandbox: true", source)
        self.assertIn("preload", source)
        self.assertIn("will-navigate", source)
        self.assertIn("setWindowOpenHandler", source)
        self.assertIn("backend.stop()", source)

    def test_backend_manager_contract(self):
        source = self.read("desktop", "backend-manager.cjs")

        # 随机可用端口，而不是固定 5000
        self.assertIn("listen(0", source)
        self.assertIn("/healthz", source)
        # 开发模式走系统 Python + run_waitress.py
        self.assertIn("run_waitress.py", source)
        self.assertIn("UROPUC_PYTHON", source)
        # 生产模式从 resources/backend/UroPUCBackend 启动打包后的后端
        self.assertIn("process.resourcesPath", source)
        self.assertIn("UroPUCBackend", source)
        self.assertIn("windowsHide: true", source)
        # Windows 退出时用 taskkill /T 连带子进程一起清理
        self.assertIn("'taskkill'", source)
        self.assertIn("'/T'", source)
        self.assertIn("'/F'", source)

    def test_preload_exposes_minimal_bridge_only(self):
        source = self.read("desktop", "preload.cjs")

        self.assertIn("contextBridge.exposeInMainWorld", source)
        # 不允许把整个 ipcRenderer 暴露给渲染进程
        self.assertNotIn("ipcRenderer,", source)
        self.assertNotIn("ipcRenderer;", source)
        self.assertNotIn("require('node:", source.replace('require("node:', ""))
        self.assertNotIn("exposeInMainWorld('ipcRenderer'", source)

    def test_pyinstaller_spec_is_onedir_whitelist_bundle(self):
        source = self.read("packaging", "UroPUCBackend.spec")

        self.assertIn("run_waitress.py", source)
        self.assertIn('name="UroPUCBackend"', source)
        # onedir：exclude_binaries=True + COLLECT，不追求 one-file
        self.assertIn("exclude_binaries=True", source)
        self.assertIn("COLLECT(", source)
        # 安装后不允许出现命令行黑框
        self.assertIn("console=False", source)

        for resource in ("templates", "static", "data/seed", "knowledge_base.xlsx"):
            self.assertIn(resource, source)
        # 白名单之外的内容（.env、api_config、私密数据）一律不得进入安装包
        after_datas = source.split("datas = [", 1)[1]
        for forbidden in (".env", "api_config", "uploads", "private"):
            self.assertNotIn(forbidden, after_datas)

    def test_build_backend_script_guards_private_data(self):
        source = self.read("packaging", "build_backend.ps1")

        self.assertIn("UroPUCBackend.spec", source)
        self.assertIn("--distpath", source)
        for private_name in ("api_config.json", ".env"):
            self.assertIn(private_name, source)

    def test_release_workflow_builds_desktop_installer(self):
        source = self.read(".github", "workflows", "release.yml")

        # 保留 Python pytest 回归
        self.assertIn("pytest", source)
        # Node LTS + npm ci
        self.assertIn("setup-node", source)
        self.assertIn("npm ci", source)
        # PyInstaller 后端 + electron-builder NSIS 安装包
        self.assertIn("build_backend.ps1", source)
        self.assertIn("--win nsis", source)
        self.assertIn("UroPUC-Setup", source)
        # 旧 C# launcher 发布链路暂不删除
        self.assertIn("build_release_packages.ps1", source)
        self.assertIn("UroPUC-windows.zip", source)


if __name__ == "__main__":
    unittest.main()
