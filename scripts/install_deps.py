import subprocess
import sys
import time
from pathlib import Path

def install_dependencies():
    max_retries = 3
    retry_delay = 5
    requirements_file = Path('requirements.txt')
    success = False
    
    print("开始安装Python依赖...")
    
    for attempt in range(max_retries):
        try:
            # 使用虚拟环境的pip安装依赖
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)],
                check=True,
                capture_output=True,
                text=True
            )
            print("依赖安装成功！")
            success = True
            break
            
        except subprocess.CalledProcessError as e:
            print(f"第 {attempt + 1} 次尝试失败:")
            print(e.stderr)
            
            # 检查特定错误并尝试修复
            if "Could not find a version" in e.stderr:
                print("检测到版本冲突，尝试放宽版本限制...")
                update_requirements(loose=True)
            elif "No matching distribution" in e.stderr:
                print("检测到不兼容的包，尝试替代方案...")
                update_requirements(replace=True)
                
            if attempt < max_retries - 1:
                print(f"{retry_delay}秒后重试...")
                time.sleep(retry_delay)
    
    if not success:
        print("依赖安装失败，请手动检查")
        sys.exit(1)
        
    # 生成更新的requirements.txt
    update_requirements_file()

def update_requirements(loose=False, replace=False):
    """根据错误调整requirements.txt"""
    requirements = []
    with open('requirements.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if loose and '==' in line:
                # 放宽版本限制
                pkg = line.split('==')[0]
                requirements.append(f"{pkg}>={line.split('==')[1]}")
            elif replace and 'PyQt5' in line:
                # 替换PyQt5为PySide6
                requirements.append(line.replace('PyQt5', 'PySide6'))
            else:
                requirements.append(line)
    
    with open('requirements.txt', 'w') as f:
        f.write('\n'.join(requirements))

def update_requirements_file():
    """生成精确的requirements.txt"""
    print("正在生成更新的requirements.txt...")
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'freeze'],
        capture_output=True,
        text=True
    )
    
    with open('requirements.txt', 'w') as f:
        f.write(result.stdout)
    print("requirements.txt已更新")

if __name__ == '__main__':
    install_dependencies()
