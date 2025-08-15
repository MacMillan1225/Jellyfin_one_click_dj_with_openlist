import requests
import logging

class OpenListAPI:
    def __init__(self, prefix_url):
        self.token = ""
        self.token_status = True

        self.prefix_url = prefix_url
        self.headers = {'Content-Type': 'application/json'}

    def validation_info(self, info_list):
        if not all(info_list):
            logging.error("认证信息不完整")
            return False
        return True

    def get_token(self, auth_info):
        logging.info("正在获取token")
        self.token_status = False
        try:
            resp = requests.post(f"{self.prefix_url}/api/auth/login", json={
                'username': auth_info["username"],
                'password': auth_info["password"],
            }, headers=self.headers)
            resp.raise_for_status()
            status_code = resp.json()["code"]
            if status_code == 200:
                data = resp.json().get('data', {})
                token = data.get('token')
                logging.info("Token 获取成功")
                return 200, token
            elif status_code in (401, 403, 400):
                logging.error("Token 获取失败，账号密码错误")
                return 401, ""
            else:
                logging.error(f"Token 验证失败：服务器返回状态码 {resp.status_code}")
                return 400, ""
        except requests.RequestException as e:
            logging.error(f"请求异常: {e}")
            return 500, ""
        except ValueError:
            logging.error("响应解析失败，非JSON格式")
            return 500, ""

    def verify_token(self, token: str):
        """验证指定 token 并返回状态字符串: success / auth_error / network_error"""
        logging.info("正在验证 Token...")
        try:
            resp = requests.get(f"{self.prefix_url}/api/me", headers={'Authorization': token}, timeout=5)
            data = resp.json()
            if resp.json()["code"] == 200:
                username = resp.json()["data"]["username"]
                logging.info(f"Token 验证成功，用户名: {username}")
                self.token = token
                self.token_status = True
                return True
            else:
                logging.error("网络连接正常，但 Token 验证失败")
                return False
        except requests.exceptions.RequestException as e:
            # 网络错误，可能是连接超时、DNS失败等
            logging.error(f"网络连接错误: {e}")
            return False

    def get_cloud_dir_info(self, path, password="", page=1, per_page=5, refresh=True):
        if not self.validation_info([self.token]):
            logging.error("请先认证获取Token")
            return None
        params = {
            "path": path,
            "password": password,
            "page": page,
            "per_page": per_page,
            "refresh": refresh
        }
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        try:
            response = requests.get(f"{self.prefix_url}/api/fs/list", params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 200:
                logging.info("云盘目录信息获取成功")
                info_dict = data.get("data")
                info_dict["path"] = path  # 添加当前路径信息
                return info_dict
            else:
                logging.error(f"获取云盘目录信息失败: {data.get('msg')}")
                return None
        except requests.RequestException as e:
            logging.error(f"请求异常: {e}")
            return None
        except ValueError:
            logging.error("响应解析失败，非JSON格式")
            return None

    def get_all_files_from_dir(self, path, password=""):
        """获取指定目录下的所有文件"""
        logging.info("正在获取文件列表")
        files_info = self.get_cloud_dir_info(path, password, 1, 9999, refresh=True)
        logging.info("获取文件列表成功")
        return files_info["content"]

    def rename_file(self, path, rename_list):
        """重命名文件"""
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        payload = {
            "src_dir": path,
            "rename_objects": rename_list
        }
        try:
            response = requests.post(f"{self.prefix_url}/api/fs/batch_rename", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 200:
                logging.info("文件重命名成功")
                return True
            else:
                logging.error(f"文件重命名失败: {data.get('content')['msg']}")
                return False
        except requests.RequestException as e:
            logging.error(f"请求异常: {e}")
            return False

    def copy_file(self, src_dir, dst_dir, file_list):
        """
        调用 Alist API 创建文件复制任务

        :param token: 身份认证 token（Authorization header）
        :param src_dir: 源文件夹路径，字符串
        :param dst_dir: 目标文件夹路径，字符串
        :param file_list: 要复制的文件名列表，例如 ["a.mp4", "b.mp4"]
        :return: True 表示启动任务成功，False 失败
        """
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }

        payload = {
            "src_dir": src_dir,
            "dst_dir": dst_dir,
            "names": file_list  # 列表
        }

        try:
            logging.info(f"正在创建复制任务:{src_dir} -> {dst_dir}")
            response = requests.post(f"{self.prefix_url}/api/fs/copy", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 200:
                logging.info("创建复制任务成功")
                return True
            else:
                logging.error(f"创建复制任务失败: {data.get('msg')}")
                return False
        except requests.RequestException as e:
            logging.error(f"请求异常: {e}")
            return False

    def mkdir(self, path):
        """
        创建新文件夹

        :param path: 新目录路径，例如 "/tt" 或 "/Video/NewSeason"
        :return: True 表示成功创建，False 表示失败
        """
        headers = {
            "Authorization": self.token,  # 已在类初始化时存储
            "Content-Type": "application/json"
        }

        payload = {
            "path": path
        }

        try:
            response = requests.post(f"{self.prefix_url}/api/fs/mkdir", json=payload, headers=headers)
            logging.info(f"正在创建目录: {path}")
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 200:
                logging.info(f"目录创建成功: {path}")
                return True
            else:
                logging.error(f"目录创建失败: {data.get('message')}")
                return False
        except requests.RequestException as e:
            logging.error(f"请求异常: {e}")
            return False

if __name__ == "__main__":
    pass