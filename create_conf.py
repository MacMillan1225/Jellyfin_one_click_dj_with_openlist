import json
import os
import sys

def resource_path(relative_path):
    """ 获取资源文件的绝对路径
        - 开发环境：返回相对于当前文件的路径
        - 打包后：返回 exe 同目录路径
    """
    if getattr(sys, 'frozen', False):  # PyInstaller 打包后
        base_path = os.path.dirname(sys.executable)
    else:                              # 源码运行
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class ConfigManager:
    def __init__(self, filename='conf.json'):
        # 使用resource_path定位配置文件
        self.filename = resource_path(filename)
        self.config = {}
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def save(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def initialize(self):
        self.config = {
            "dest": "",
            "username": "",
            "password": "",
            "token": "",
            "base_dir": "",
            "dst_dir": ""
        }
        self.save()


if __name__ == '__main__':
    config_manager = ConfigManager()
    config_manager.set('example_key', 'example_value')
    print(config_manager.get('example_key'))  # Output: example_value
    print(config_manager.get('non_existent_key', 'default_value'))  # Output: default_value
    config_manager.save()  # Save changes to configuration file