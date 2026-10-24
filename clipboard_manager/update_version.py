import sys
import re

def update_version(new_version):
    iss_file = "d:/daima/kjj/clipboard_manager/setup_script.iss"
    main_file = "d:/daima/kjj/clipboard_manager/main.py"
    readme_file = "d:/daima/kjj/README.md"
    
    # 1. Update ISS file
    with open(iss_file, "r", encoding="utf-8") as f:
        iss_content = f.read()
    
    iss_content = re.sub(r'(?m)^AppVersion=.*', f'AppVersion={new_version}', iss_content)
    
    with open(iss_file, "w", encoding="utf-8") as f:
        f.write(iss_content)
    print(f"Updated {iss_file} to version {new_version}")

    # 2. Update main.py
    with open(main_file, "r", encoding="utf-8") as f:
        main_content = f.read()
    
    main_content = re.sub(r'APP_VERSION\s*=\s*".*?".*', f'APP_VERSION = "{new_version}" # 全局统一版本号', main_content)
    
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(main_content)
    print(f"Updated {main_file} to version {new_version}")
    
    # 3. Update README.md
    with open(readme_file, "r", encoding="utf-8") as f:
        readme_content = f.read()
    
    # 更新顶部徽章
    readme_content = re.sub(r'!\[Version\]\(https://img\.shields\.io/badge/Version-.*?-(.*?)\)', f'![Version](https://img.shields.io/badge/Version-{new_version}-\\1)', readme_content)
    # 更新底部交流与反馈区域的版本号
    readme_content = re.sub(r'\*\*当前最新版本\*\*：v.*', f'**当前最新版本**：v{new_version}', readme_content)
    
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print(f"Updated {readme_file} to version {new_version}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_version.py <new_version>")
        sys.exit(1)
    update_version(sys.argv[1])
