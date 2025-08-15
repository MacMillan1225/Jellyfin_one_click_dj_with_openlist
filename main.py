import asyncio
import logging
import math
import os
import re
from pathlib import Path

import tui
from colorama import init
from create_conf import ConfigManager
from oplist_api import OpenListAPI

from pypinyin import lazy_pinyin, Style

init(autoreset=True)

formatter = logging.Formatter('[%(levelname)s][%(asctime)s][%(filename)s] %(message)s',
                              datefmt='%H:%M:%S')

# TUI 日志适配器
class TUILogHandler(logging.Handler):
    def __init__(self, app):
        super().__init__()
        self.app = app
    def emit(self, record):
        msg = self.format(record)
        self.app.post_message(tui.LogMessage(msg, record.levelno))

# 全局变量
DEST_URL = ""
config_manager = ConfigManager()
oplist_api = OpenListAPI("")
tui_app: tui.FileSelectorApp

# 拼音转换
def hanzi_to_pinyin_until_symbol(text):
    """
    将字符串开头的 “汉字、英文、数字、合法符号” 提取出来，
    汉字转成拼音（首字母大写），英文/数字/符号保留。
    返回 (pinyin_str, original_str)
    """

    # 定义合法字符类：
    # \u4e00-\u9fff 匹配中文汉字
    # A-Za-z         英文字母
    # 0-9            数字
    # _-             合法符号（你可自行增加）
    pattern = r"^[\u4e00-\u9fffA-Za-z0-9_-]+"

    match = re.match(pattern, text)
    if not match:
        return "", ""

    original_str = match.group()

    # 把汉字转成拼音（首字母大写），其他字符保留
    pinyin_list = []
    for ch in original_str:
        if '\u4e00' <= ch <= '\u9fff':  # 汉字
            py = lazy_pinyin(ch, style=Style.NORMAL)[0]
            pinyin_list.append(py.capitalize())
        else:
            pinyin_list.append(ch)

    pinyin_str = ''.join(pinyin_list)
    return pinyin_str, original_str

# 异步输入函数
async def tui_input(prompt: str, default_value="", placeholder="输入后按回车确认", ):
    global tui_app
    future = asyncio.Future()

    async def callback(value):
        if not future.done():
            future.set_result(value)

    await tui_app.show_input(prompt, callback, default_value, placeholder)
    result = await future
    await tui_app.children[0].remove_children(selector="#input_dialog")  # 移除输入弹窗
    return result

# ----------- 业务逻辑部分全部改 async -------------
async def get_config():
    """读取配置并检查每个参数"""
    global DEST_URL, config_manager
    para_list = ["dest", "username", "password", "token", "base_dir", "dst_dir"]

    logging.info("尝试读取配置文件")
    config_manager.load()
    try:
        for key in para_list:
            value = config_manager.get(key, "")
            if isinstance(value, str) and value.strip() == "":
                logging.warning(f"配置项 '{key}' 为空")
            else:
                logging.info(f"配置项 '{key}' 已加载: {value}")
                if key == "dest":
                    DEST_URL = value
    except Exception:
        # 如果 dest 未加载，则初始化默认配置
        logging.error("读取配置文件失败，创建默认配置文件")
        config_manager.initialize()
        logging.info("默认配置文件创建成功")

async def check_info():
    global config_manager
    if config_manager.get("username", "") == "" or config_manager.get("password", "") == "":
        await reset_auth_info()
    if config_manager.get("dest", "") == "":
        await reset_dest_url()
    if config_manager.get("base_dir", "") == "" or config_manager.get("dst_dir", "") == "":
        await reset_dir_info()

async def get_auth_config():
    """补全缺失参数"""
    global config_manager
    auth_info = {
        'username': config_manager.get("username", "").strip(),
        'password': config_manager.get("password", "").strip()
    }
    logging.info("账号密码读取成功")
    return auth_info

async def reset_dir_info():
    """重置 base_dir 和 dst_dir"""
    global config_manager
    logging.info("请设置 base_dir 和 dst_dir")
    config_manager.set('base_dir', (await tui_input("请输入Openlist中视频源目录:", placeholder="/夸克云盘/分享")).strip())
    config_manager.set('dst_dir', (await tui_input("请输入Openlist中媒体库目录:", placeholder="/Jellyfin/media")).strip())
    config_manager.save()
    logging.info("base_dir 和 dst_dir 配置成功")
    return

async def reset_auth_info():
    """重置账号密码"""
    global config_manager
    logging.info("请重设用户名和密码")
    config_manager.set('username', (await tui_input("请输入Openlist用户名:", placeholder="admin")).strip())
    config_manager.set('password', (await tui_input("请输入Openlist用户密码:", placeholder="passwd")).strip())
    config_manager.save()
    logging.info("账号密码配置成功")
    return

async def reset_dest_url():
    """重置目标URL"""
    global config_manager, DEST_URL
    logging.info("请重设目标URL")
    new_dest = (await tui_input("请输入OpenList访问URL:", placeholder="http://127.0.0.1:5244")).strip()
    config_manager.set('dest', new_dest)
    config_manager.save()
    DEST_URL = new_dest
    logging.info(f"目标URL已更新为: {DEST_URL}")
    return

async def authenticate(auth_info):
    global config_manager, oplist_api
    token = config_manager.get("token", "")
    if token != "":
        if oplist_api.verify_token(token):
            logging.info("Token 验证成功")
            return
        else:
            logging.warning("Token 验证失败，尝试重新获取 Token")
    else:
        logging.info("Token 为空，尝试获取新的 Token")
    status_code, token = oplist_api.get_token(auth_info)
    if status_code == 200:
        logging.info("Token 获取成功，重新验证...")
        if oplist_api.verify_token(token):
            logging.info("Token 正在写入文件")
            config_manager.set('token', token)
            config_manager.save()
            return
    elif status_code == 401:
        logging.error("账号密码错误，请重新设置")
        await reset_auth_info()
        auth_info = await get_auth_config()
        await authenticate(auth_info)
    elif status_code == 500:
        logging.error("网络连接失败或服务器错误，请检查网络设置")
        await reset_dest_url()
        oplist_api.prefix_url = DEST_URL
        await authenticate(auth_info)

async def choose_path(mode="base"):
    global config_manager, oplist_api
    while True:
        path = config_manager.get(f'{mode}_dir')
        dir_info = oplist_api.get_cloud_dir_info(path=path)
        if not dir_info:
            promot = "源" if mode == "base" else "媒体库"
            logging.error(f"获取云端目录信息失败，请重新设置 {promot} 路径")
            path = await tui_input(f"请输入新的 {promot} 路径:")
            config_manager.set(f'{mode}_dir', path)
            config_manager.save()
            continue
        else:
            return dir_info

async def show_file_browser(content_dict):
    global tui_app, oplist_api
    future = asyncio.Future()
    async def callback(value):
        if not future.done():
            future.set_result(value)
    await tui_app.show_file_browser(oplist_api, content_dict, callback)
    result = await future
    await tui_app.show_welcome()
    return result

def rename_video_file(filename, prefix, season=1, digits=2):
    """
    根据视频文件名提取结尾数字并重命名为指定格式。

    :param filename: 原始文件名（包含扩展名）
    :param prefix: 前缀，比如 "TV show"
    :param season: 季数，默认 1
    :param digits: 集数占用的位数，默认 2
    :return: 新文件名，如果不是视频文件返回原始文件名
    """
    # 常见视频扩展
    video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.flv'}

    # 分离文件名和扩展名
    name, ext = os.path.splitext(filename)
    ext_lower = ext.lower()

    # 不是视频文件就直接返回原文件名
    if ext_lower not in video_exts:
        return filename

    # 从末尾提取数字（最后一段连续数字）
    match = re.search(r'(\d+)\D*$', name)
    if not match:
        # 找不到数字，保留原文件名
        return filename

    episode_num = int(match.group(1))

    # 格式化新文件名：TV show S01E01.mp4
    new_filename = f"{prefix} S{season:02d}E{episode_num:0{digits}d}{ext_lower}"
    return new_filename

async def form_rename_file_list(file_list, name_prefix="", season=1):
    """处理文件列表，生成重命名后的文件列表"""
    file_rename_list = []
    file_count = len(file_list)
    for file in file_list:
        file_name = file["name"]
        new_file_name = rename_video_file(file_name, name_prefix, season, digits=int(math.log10(file_count))+1)
        if new_file_name != file_name:
            logging.info(f"重命名: {file_name} -> {new_file_name}")
            file_rename_list.append({
                "src_name": file_name,
                "new_name": new_file_name,
            })
    return file_rename_list

async def auto_rename(path, default_name="TV show", season=1):
    """自动重命名文件"""
    global oplist_api, tui_app
    file_list = oplist_api.get_all_files_from_dir(path)
    name_prefix = await tui_input(f"请输入剧集名称:", placeholder="TV show", default_value=default_name)
    logging.info("正在处理文件列表...")
    file_rename_list = await form_rename_file_list(file_list, name_prefix, season)
    logging.info("文件列表处理完成，准备重命名...")
    oplist_api.rename_file(path, file_rename_list)
    return file_rename_list

async def auto_fs_structure(path, default_name="TV show"):
    """自动创建文件夹结构"""
    global oplist_api, tui_app
    show_name = await tui_input("请输入剧集名称:", placeholder="一起去看流星雨", default_value=default_name)
    season = await tui_input("请输入季数:", placeholder="01", default_value="01")
    logging.info("正在创建文件夹结构...")
    new_dir_path = str(Path(path) / show_name / f"Season {season.zfill(2)}")
    oplist_api.mkdir(new_dir_path)
    logging.info(f"创建完成！路径为: {new_dir_path}")
    return new_dir_path

async def form_copy_file_list(file_list):
    """处理文件列表，生成复制的文件列表"""
    file_copy_list = []
    for file in file_list:
        file_name = file["name"]
        file_copy_list.append(file_name)
    return file_copy_list

async def auto_copy_file(path, dst_path):
    """自动复制文件"""
    global oplist_api
    file_list = oplist_api.get_all_files_from_dir(path)
    if not file_list:
        logging.warning("源目录没有文件，无法进行复制")
        return

    logging.info(f"正在复制 {len(file_list)} 个文件到目标目录 {dst_path}...")
    copy_file_list = await form_copy_file_list(file_list)
    oplist_api.copy_file(path, dst_path, copy_file_list)

# 异步主逻辑
async def main_logic():
    global oplist_api, tui_app, config_manager, DEST_URL

    await get_config()
    await check_info()
    auth_info = await get_auth_config()

    oplist_api = OpenListAPI(DEST_URL)

    await authenticate(auth_info)
    logging.info("正在配置 OpenlistAPI")

    # 选择源地址
    base_content_data = await choose_path(mode="base")
    logging.info("获得源地址路径")
    select_base_path = await show_file_browser(base_content_data)
    logging.info(f"已选定源地址目录\"{select_base_path}\"")

    # 获取拼音和原始名称
    py_name, hz_name = hanzi_to_pinyin_until_symbol(Path(select_base_path).name)

    # 重命名部分
    file_rename_list = await auto_rename(select_base_path, py_name)
    hz_name = hz_name + f"（{len(file_rename_list)}集）"

    # 选择目标地址
    dst_content_data = await choose_path(mode="dst")
    logging.info("获得目标地址路径")
    select_dst_path = await show_file_browser(dst_content_data)
    logging.info(f"已选定目标地址目录\"{select_dst_path}\"")

    # 创建结构文件夹
    select_video_path = await auto_fs_structure(select_dst_path, hz_name)

    # 进行文件复制
    logging.info(f"开始复制文件到目标目录\"{select_video_path}\"")
    await auto_copy_file(select_base_path, select_video_path)
    logging.info("完成！")

    # 关闭命令
    tui_app.exit()

# UI 启动
def ui():
    global tui_app
    tui_app = tui.FileSelectorApp(main_logic)  # 直接传 async 的 main_logic
    tui_handler = TUILogHandler(tui_app)
    tui_handler.setFormatter(formatter)
    logging.getLogger().addHandler(tui_handler)
    logging.getLogger().setLevel(logging.INFO)
    tui_app.run()

if __name__ == '__main__':
    ui()