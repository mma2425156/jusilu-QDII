import subprocess
import sys

def run_scripts():
    try:
        print("开始运行爬虫脚本...")
        subprocess.run([sys.executable, "qdii_spider.py"], check=True)
        print("爬虫脚本运行完成")
        
        print("启动web应用...")
        subprocess.run([sys.executable, "web_ui/app.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"脚本执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_scripts()
