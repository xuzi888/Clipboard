import json
import os
import sys
import uuid

class SnippetsManager:
    def __init__(self, data_file=None):
        if data_file is None:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(os.path.abspath(sys.executable))
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            data_file = os.path.join(base_path, "data.json")
                    
        self.data_file = data_file
        self.data = {"history": [], "snippets": {"scenes": []}}
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    
                    # 兼容老数据结构：如果直接是列表（旧 history）或者只包含 scenes（旧 snippets）
                    if isinstance(file_data, list):
                        self.data = {"history": file_data, "snippets": {"scenes": []}}
                    else:
                        self.data = file_data
                        if "snippets" not in self.data:
                            self.data["snippets"] = {"scenes": []}
                        if "history" not in self.data:
                            self.data["history"] = []
                            
                    # 兼容快捷短语的更老版本数据结构（之前是 groups -> scenes，现在是 scenes -> groups）
                    snippets_data = self.data["snippets"]
                    if "groups" in snippets_data and "scenes" not in snippets_data:
                        old_groups = snippets_data.pop("groups")
                        new_scenes = []
                        for og in old_groups:
                            new_scene = {
                                "id": og.get("id", self.generate_id()),
                                "name": og.get("name", "未命名"),
                                "groups": []
                            }
                            for os_item in og.get("scenes", []):
                                new_group = {
                                    "id": os_item.get("id", self.generate_id()),
                                    "name": os_item.get("name", "未命名"),
                                    "phrases": os_item.get("phrases", [])
                                }
                                new_scene["groups"].append(new_group)
                            new_scenes.append(new_scene)
                        snippets_data["scenes"] = new_scenes
                        self.save_data()
                        
            except Exception as e:
                print(f"加载数据失败: {e}")
                self.data = {"history": [], "snippets": {"scenes": []}}
        else:
            self.data = {"history": [], "snippets": {"scenes": []}}
            self.save_data()

    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存快捷短语数据失败: {e}")

    def generate_id(self):
        return str(uuid.uuid4())

    def get_scenes(self):
        return self.data.get("snippets", {}).get("scenes", [])

    def add_scene(self, name):
        scene = {
            "id": self.generate_id(),
            "name": name,
            "groups": []
        }
        self.data.setdefault("snippets", {}).setdefault("scenes", []).append(scene)
        self.save_data()
        return scene

    def edit_scene(self, scene_id, new_name):
        for s in self.data.get("snippets", {}).get("scenes", []):
            if s["id"] == scene_id:
                s["name"] = new_name
                self.save_data()
                return True
        return False

    def delete_scene(self, scene_id):
        if "scenes" in self.data.get("snippets", {}):
            self.data["snippets"]["scenes"] = [s for s in self.data["snippets"]["scenes"] if s["id"] != scene_id]
            self.save_data()
        return True

    def add_group(self, scene_id, name):
        for s in self.data.get("snippets", {}).get("scenes", []):
            if s["id"] == scene_id:
                group = {
                    "id": self.generate_id(),
                    "name": name,
                    "phrases": []
                }
                s.setdefault("groups", []).append(group)
                self.save_data()
                return group
        return None

    def edit_group(self, scene_id, group_id, new_name):
        for s in self.data.get("snippets", {}).get("scenes", []):
            if s["id"] == scene_id:
                for g in s.get("groups", []):
                    if g["id"] == group_id:
                        g["name"] = new_name
                        self.save_data()
                        return True
        return False

    def delete_group(self, scene_id, group_id):
        for s in self.data.get("snippets", {}).get("scenes", []):
            if s["id"] == scene_id:
                if "groups" in s:
                    s["groups"] = [g for g in s["groups"] if g["id"] != group_id]
                    self.save_data()
                return True
        return False

    def get_phrases(self, scene_id, group_id):
        for s in self.data.get("snippets", {}).get("scenes", []):
            if s["id"] == scene_id:
                for g in s.get("groups", []):
                    if g["id"] == group_id:
                        return g.get("phrases", [])
        return []

    def add_phrase(self, scene_id, group_id, content, item_type="text", remark=""):
        import time
        for s in self.data.get("snippets", {}).get("scenes", []):
            if s["id"] == scene_id:
                for g in s.get("groups", []):
                    if g["id"] == group_id:
                        phrase = {
                            "id": self.generate_id(),
                            "type": item_type,
                            "content": content,
                            "remark": remark,
                            "created_at": time.time()
                        }
                        g.setdefault("phrases", []).insert(0, phrase)
                        self.save_data()
                        return phrase
        return None

    def edit_phrase(self, scene_id, group_id, phrase_id, new_content, new_scene_id=None, new_group_id=None, new_remark=None):
        target_phrase = None
        
        # 1. 查找并更新内容
        for s in self.data.get("snippets", {}).get("scenes", []):
            if s["id"] == scene_id:
                for g in s.get("groups", []):
                    if g["id"] == group_id:
                        for p in g.get("phrases", []):
                            if p["id"] == phrase_id:
                                p["content"] = new_content
                                if new_remark is not None:
                                    p["remark"] = new_remark
                                target_phrase = p
                                break
                        break
                break
                
        if not target_phrase:
            return False
            
        # 2. 如果场景或分组发生了变化，需要移动短语
        if (new_scene_id and new_scene_id != scene_id) or (new_group_id and new_group_id != group_id):
            new_s_id = new_scene_id if new_scene_id else scene_id
            new_g_id = new_group_id if new_group_id else group_id
            
            # 从原分组删除
            self.delete_phrase(scene_id, group_id, phrase_id)
            
            # 找到新分组并添加
            for s in self.data.get("snippets", {}).get("scenes", []):
                if s["id"] == new_s_id:
                    for g in s.get("groups", []):
                        if g["id"] == new_g_id:
                            if "phrases" not in g:
                                g["phrases"] = []
                            g["phrases"].append(target_phrase)
                            break
                    break
                    
        self.save_data()
        return True

    def delete_phrase(self, scene_id, group_id, phrase_id):
        for s in self.data.get("snippets", {}).get("scenes", []):
            if s["id"] == scene_id:
                for g in s.get("groups", []):
                    if g["id"] == group_id:
                        g["phrases"] = [p for p in g.get("phrases", []) if p["id"] != phrase_id]
                        self.save_data()
                        return True
        return False
        
    def export_data(self, file_path):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data.get("snippets", {}), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"导出数据失败: {e}")
            return False

    def import_data(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_snippets = json.load(f)
                
            if "scenes" not in imported_snippets:
                # 兼容旧版本只导出 groups 的情况
                if "groups" in imported_snippets:
                    old_groups = imported_snippets.pop("groups")
                    new_scenes = []
                    for og in old_groups:
                        new_scene = {
                            "id": og.get("id", self.generate_id()),
                            "name": og.get("name", "未命名"),
                            "groups": []
                        }
                        for os_item in og.get("scenes", []):
                            new_group = {
                                "id": os_item.get("id", self.generate_id()),
                                "name": os_item.get("name", "未命名"),
                                "phrases": os_item.get("phrases", [])
                            }
                            new_scene["groups"].append(new_group)
                        new_scenes.append(new_scene)
                    imported_snippets["scenes"] = new_scenes
                else:
                    return False
                    
            self.data.setdefault("snippets", {})["scenes"] = imported_snippets["scenes"]
            self.save_data()
            return True
        except Exception as e:
            print(f"导入数据失败: {e}")
            return False
