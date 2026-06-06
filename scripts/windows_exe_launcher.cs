using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Windows.Forms;

internal static class WindowsExeLauncher
{
    private const string AppTitle = "AI罕见病助手";

    [STAThread]
    private static int Main()
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        string launcher = Path.Combine(baseDir, "windows_launcher.pyw");
        if (!File.Exists(launcher))
        {
            MessageBox.Show("没有找到 windows_launcher.pyw。请先解压完整的 Windows ZIP 安装包，再双击本程序。", AppTitle, MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return 2;
        }

        string pythonw = FindPythonw();
        if (String.IsNullOrEmpty(pythonw))
        {
            MessageBox.Show("没有找到 Python 3.10+。请先安装 Python，或确认 D:\\anaconda\\pythonw.exe 可用，然后重新打开本程序。", AppTitle, MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return 3;
        }

        try
        {
            ProcessStartInfo info = new ProcessStartInfo
            {
                FileName = pythonw,
                Arguments = Quote(launcher),
                WorkingDirectory = baseDir,
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden
            };
            Process.Start(info);
            return 0;
        }
        catch (Exception exc)
        {
            MessageBox.Show("启动失败：\n" + exc.Message, AppTitle, MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 4;
        }
    }

    private static string FindPythonw()
    {
        string[] directCandidates =
        {
            Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ".venv", "Scripts", "pythonw.exe"),
            @"D:\anaconda\pythonw.exe",
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Python")
        };

        foreach (string candidate in directCandidates)
        {
            if (File.Exists(candidate))
            {
                return candidate;
            }
            if (Directory.Exists(candidate))
            {
                string found = Directory.GetFiles(candidate, "pythonw.exe", SearchOption.AllDirectories).OrderByDescending(x => x).FirstOrDefault();
                if (!String.IsNullOrEmpty(found))
                {
                    return found;
                }
            }
        }

        string pathEnv = Environment.GetEnvironmentVariable("PATH") ?? "";
        foreach (string dir in pathEnv.Split(Path.PathSeparator))
        {
            try
            {
                string candidate = Path.Combine(dir.Trim(), "pythonw.exe");
                if (File.Exists(candidate))
                {
                    return candidate;
                }
            }
            catch
            {
                // Ignore malformed PATH entries.
            }
        }
        return "";
    }

    private static string Quote(string value)
    {
        return "\"" + value.Replace("\"", "\\\"") + "\"";
    }
}
