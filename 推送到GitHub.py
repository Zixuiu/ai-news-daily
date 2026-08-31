# -*- coding: utf-8 -*-
"""ai-news-daily 专用推送工具：把本仓库 main 推到 github.com/Zixuiu/ai-news-daily。
- 自动提交未提交的改动（main.py 等），再推送。
- GitHub token 优先级：环境变量 GITHUB_TOKEN > 本地文件 ~/.ssh/github_token（不入库）。
- 网络(github.com)不通时自动重试，最长约 15 分钟；遇到非网络错误则停下提示。
运行：python 推送到GitHub.py
"""
import os
import sys
import time
import datetime
import subprocess

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
GIT = "D:\\Git\\cmd\\git.exe"
GIT_REMOTE = "github.com/Zixuiu/ai-news-daily.git"
MAX_SECONDS = 900
AUTHOR_EMAIL = "1399972370@qq.com"
AUTHOR_NAME = "PC-action"

NET_KEYS = [
    "Could not resolve host", "Connection reset", "Connection refused",
    "unable to access", "Timed out", "Empty reply", "EOF", "Failed to connect",
    "Recv failure", "could not read Password", "hung up", "RPC failed",
    "Sabotaged", "Operation timed out",
]


def log(msg, level="INFO"):
    prefix = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(level, "•")
    print(f"{prefix} {msg}")


def read_token():
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        return tok
    tf = os.path.join(os.path.expanduser("~"), ".ssh", "github_token")
    if not os.path.exists(tf):
        return None
    raw = open(tf, "rb").read()
    for enc in ("utf-8", "utf-16", "utf-8-sig", "gbk"):
        try:
            return raw.decode(enc).strip()
        except Exception:
            continue
    return None


def git(*args, timeout=600):
    try:
        return subprocess.run([GIT, "-C", REPO_DIR, *args],
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return type("R", (), {"returncode": -1, "stdout": "", "stderr": "超时"})()
    except Exception as e:
        return type("R", (), {"returncode": -1, "stdout": "", "stderr": str(e)})()


def commit_pending():
    """暂存并提交所有可提交改动；无改动则跳过。返回是否发生了提交。"""
    git("add", "-A")
    if git("diff", "--cached", "--quiet").returncode == 0:
        log("没有需要提交的新更改")
        return False
    staged = [l for l in git("diff", "--cached", "--name-only").stdout.splitlines() if l.strip()]
    log(f"将提交 {len(staged)} 个文件: {', '.join(staged[:8])}"
        + (" ..." if len(staged) > 8 else ""))
    msg = f"auto push {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    r = git("-c", f"user.email={AUTHOR_EMAIL}", "-c", f"user.name={AUTHOR_NAME}",
            "commit", "-m", msg)
    if r.returncode == 0:
        log("已提交", "SUCCESS")
        return True
    log("提交失败: " + (r.stderr.strip() or r.stdout.strip())[:400], "ERROR")
    return False


def push_with_retry(dest):
    os.environ["GIT_TERMINAL_PROMPT"] = "0"
    start = time.time()
    n = 0
    while True:
        n += 1
        r = git("push", dest, "HEAD:main", timeout=300)
        out = (r.stdout or "") + (r.stderr or "")
        print(f"    [第{n}次推送] 退出码={r.returncode}  {out.strip()[-220:]}")
        if r.returncode == 0:
            log("推送到 GitHub ai-news-daily 成功", "SUCCESS")
            return True
        if not any(k in out for k in NET_KEYS):
            log("遇到非网络错误，已停止（请人工查看上面的输出）", "ERROR")
            return False
        if time.time() - start > MAX_SECONDS:
            log("超过15分钟仍未连通 github.com，请稍后再跑一次", "WARNING")
            return False
        time.sleep(3)


def main():
    print("=" * 70)
    print("🚀 ai-news-daily → GitHub 专用推送工具")
    print("=" * 70)
    print(f"📁 仓库目录: {REPO_DIR}")

    branch = git("branch", "--show-current").stdout.strip()
    log(f"当前分支: {branch or '(detached)'}")

    token = read_token()
    if not token:
        log("未找到 GitHub token：请设 GITHUB_TOKEN 环境变量，或在 ~/.ssh/github_token 写入 token", "ERROR")
        return 1

    commit_pending()
    dest = f"https://{token}@{GIT_REMOTE}"
    ok = push_with_retry(dest)
    print("=" * 70)
    if ok:
        print("✅ 完成：ai-news-daily 已推送到 https://" + GIT_REMOTE)
    else:
        print("⚠️ 未推送成功。GitHub 网络不稳定时可稍后再跑本脚本（会自动重试）。")
    print("=" * 70)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())