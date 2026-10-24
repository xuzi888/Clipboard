import json
import os
import shutil
import subprocess

def build():
    print("====================================")
    print("  准备打包 KJJ 快捷剪贴板")
    print("====================================")
    
    # 0. 自动同步版本号
    print("\n-> 正在同步版本号...")
    try:
        subprocess.run(["python", "sync_version.py"], check=True)
    except subprocess.CalledProcessError:
        print("-> 版本号同步失败，请检查 sync_version.py 是否存在且运行正常。")
        return

    data_file = "data.json"
    backup_file = "data_backup.json"
    
    config_file = "config.json"
    config_backup_file = "config_backup.json"
    
    # 1. 备份并清空本地数据（历史记录），避免用户的个人剪贴板数据被打包给其他人
    if os.path.exists(data_file):
        shutil.copy2(data_file, backup_file)
        print("-> 已将您当前的本地数据备份至 data_backup.json")
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 清空所有数据，包括历史记录和快捷短语，确保打包出一个纯净版
            data['history'] = []
            data['snippets'] = {"scenes": []}
            
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print("-> 已成功清空 data.json 中的所有数据（包含历史记录和快捷短语）。")
        except Exception as e:
            print(f"-> 处理 data.json 失败: {e}")
            
    # 1.5 备份并重置偏好设置，避免开发者的设置被打包
    if os.path.exists(config_file):
        shutil.copy2(config_file, config_backup_file)
        print("-> 已将您当前的偏好设置备份至 config_backup.json")
        
        try:
            # 写入默认的偏好设置
            default_config = {
                "retain_days": 7,
                "hotkey": "alt+v",
                "theme": "light",
                "enable_image": True
            }
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            print("-> 已成功重置 config.json 为默认设置。")
        except Exception as e:
            print(f"-> 处理 config.json 失败: {e}")
            
    # 2. 运行 PyInstaller 进行打包
    print("\n-> 正在运行 PyInstaller (这可能需要几分钟时间)...")
    
    # 根据是否在虚拟环境中，选择正确的 pyinstaller 路径
    pyinstaller_path = os.path.join("venv", "Scripts", "pyinstaller")
    if not os.path.exists(pyinstaller_path + ".exe"):
        pyinstaller_path = "pyinstaller"
        
    try:
        subprocess.run([pyinstaller_path, "-y", "ClipboardManager.spec"], check=True)
        print("-> PyInstaller 打包完成！")
    except subprocess.CalledProcessError:
        print("-> PyInstaller 打包失败！")
        # 即使失败也要恢复数据
        
    # 3. 恢复备份的数据
    if os.path.exists(backup_file):
        shutil.move(backup_file, data_file)
        print("\n-> 已成功恢复您的本地开发数据。")
        
    if os.path.exists(config_backup_file):
        shutil.move(config_backup_file, config_file)
        print("-> 已成功恢复您的偏好设置。")
        
    # 从 main.py 读取 APP_NAME
    app_name = "KJJ 快捷剪贴板"
    try:
        import re
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'APP_NAME\s*=\s*"([^"]+)"', content)
            if match:
                app_name = match.group(1)
    except:
        pass

    print("\n-> 正在生成绿色免安装版 (ZIP格式)...")
    try:
        dist_dir = "dist"
        app_dir_name = app_name
        zip_name = os.path.join(dist_dir, f"{app_name}-绿色免安装版")
        
        # 切换到 dist 目录，将文件夹打包
        current_dir = os.getcwd()
        try:
            os.chdir(dist_dir)
            shutil.make_archive(f"{app_name}-绿色免安装版", 'zip', ".", app_dir_name)
        finally:
            os.chdir(current_dir)
        
        print(f"-> 绿色免安装版已生成: dist\\{app_name}-绿色免安装版.zip")
    except Exception as e:
        print(f"-> 生成绿色免安装版失败: {e}")

    print("\n====================================")
    print("打包流程结束！")
    print("-> 正在自动运行 Inno Setup 编译安装程序 (setup_script.iss)...")
    
    # 5. 自动运行 Inno Setup 生成安装包
    inno_setup_compiler = r"C:\Users\27859\AppData\Local\Programs\Inno Setup 6\ISCC.exe" # 默认安装路径，如果不同请修改
    if not os.path.exists(inno_setup_compiler):
        inno_setup_compiler = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    
    if os.path.exists(inno_setup_compiler):
        try:
            subprocess.run([inno_setup_compiler, "setup_script.iss"], check=True)
            print("-> 安装程序生成成功！请在 dist 目录下查看。")
        except subprocess.CalledProcessError:
            print("-> 安装程序生成失败！请手动打开 setup_script.iss 编译。")
    else:
        print(f"-> 找不到 Inno Setup 编译器 ({inno_setup_compiler})，请手动打开 setup_script.iss 编译。")

    print("====================================")

if __name__ == "__main__":
    build()