import os
import re

def sync_version():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_py_path = os.path.join(base_dir, 'main.py')
    setup_script_path = os.path.join(base_dir, 'setup_script.iss')

    # 从 main.py 读取配置
    version = None
    app_name = None
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
        v_match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', content)
        if v_match:
            version = v_match.group(1)
        n_match = re.search(r'APP_NAME\s*=\s*"([^"]+)"', content)
        if n_match:
            app_name = n_match.group(1)

    if not version:
        print("未在 main.py 中找到 APP_VERSION")
        return

    print(f"找到当前配置: 版本号={version}, 软件名称={app_name}")

    # 更新 setup_script.iss
    if os.path.exists(setup_script_path):
        with open(setup_script_path, 'r', encoding='utf-8') as f:
            iss_content = f.read()
        
        # 替换版本号
        new_iss_content = re.sub(
            r'(?m)^AppVersion=.*', 
            f'AppVersion={version}', 
            iss_content
        )
        
        # 如果获取到了软件名称，也进行同步（替换掉之前硬编码的名称）
        if app_name:
            # 找到旧的 AppName，以便在后续路径中进行精准替换
            old_name_match = re.search(r'(?m)^AppName=(.*)', iss_content)
            if old_name_match:
                old_name = old_name_match.group(1).strip()
                if old_name != app_name:
                    print(f"发现软件名称变更: {old_name} -> {app_name}，正在同步到 ISS 和 Spec 文件...")
                    new_iss_content = new_iss_content.replace(old_name, app_name)
            else:
                new_iss_content = re.sub(r'(?m)^AppName=.*', f'AppName={app_name}', new_iss_content)

        with open(setup_script_path, 'w', encoding='utf-8') as f:
            f.write(new_iss_content)
        
        print("已成功同步版本号及名称到 setup_script.iss")
    else:
        print("未找到 setup_script.iss 文件")
        
    # 同步软件名称到 ClipboardManager.spec
    spec_path = os.path.join(base_dir, 'ClipboardManager.spec')
    if app_name and os.path.exists(spec_path):
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec_content = f.read()
            
        new_spec_content = re.sub(r"name='[^']+'", f"name='{app_name}'", spec_content)
        
        with open(spec_path, 'w', encoding='utf-8') as f:
            f.write(new_spec_content)
        print("已成功同步名称到 ClipboardManager.spec")

if __name__ == '__main__':
    sync_version()
