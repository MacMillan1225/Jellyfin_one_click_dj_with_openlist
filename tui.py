from textual import events
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Input, RichLog, Static, ListView, ListItem, Label
from textual.message import Message
from pathlib import Path
import logging
import asyncio
import oplist_api

class LogMessage(Message):
    def __init__(self, text: str, level=logging.INFO):
        super().__init__()
        self.text = text
        self.level = level

class WelcomeScreen(Static):
    """启动时显示的欢迎界面"""
    def compose(self) -> ComposeResult:
        yield Static("👋 欢迎使用 OpenList 客户端", id="welcome_text")
        yield Static("请按提示在日志区完成配置", id="welcome_hint")

class InputDialog(Static):
    """模态输入弹窗"""
    def __init__(self, prompt: str, callback, default_value, placeholder, **kwargs):
        super().__init__(**kwargs)
        self.input = None
        self.input: Input
        self.prompt = prompt
        self.callback = callback
        self.placeholder = placeholder
        self.default_value = default_value

    def compose(self) -> ComposeResult:
        # 弹窗本体
        self.input = Input(placeholder=self.placeholder, id="input_field")
        box = Vertical(
            Static(self.prompt, id="input_prompt"),
            self.input
        )
        yield box

    def on_mount(self):
        self.input.focus()
        self.input.value = self.default_value

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value
        await self.callback(value)
        # 移除自己（关闭弹窗）
        await self.remove()

class FileBrowser(Static):
    """交互式文件管理器"""
    CURSOR_STYLE = "reverse"  # 高亮选中行

    def __init__(self, opapi:oplist_api.OpenListAPI, content_dict, callback, **kwargs):
        super().__init__(**kwargs)
        self.cur_path = None
        self.vertical = None
        self.list_view = None
        self.cur_path: Label
        self.vertical: Vertical
        self.list_view: ListView
        self.callback = callback      # 用户最终选择的回调
        self.items = content_dict["content"]
        self.opapi = opapi  # OpenList API 实例
        self.current_path: Path = Path(content_dict["path"])  # 当前路径

    def compose(self):
        self.list_view = ListView(*[
            ListItem()
        ], initial_index=0)

        self.cur_path = Label(f"当前路径: {self.current_path}", id="current_path")
        self.vertical = Vertical(
            Label("使用 ↑ ↓ 键选择，→ 进入文件夹，← 返回上级，回车选择"),
            self.list_view,
            self.cur_path
        )

        yield self.vertical

    def on_mount(self):
        self._refresh_list()
        self.list_view.focus()

    def _format_name(self, item):
        icon = "📁" if item["is_dir"] else "📄"
        return f"{icon} {item['name']}"

    async def on_key(self, event: events.Key):
        key = event.key
        if key == "up":
            pass
        elif key == "down":
            pass
        elif key == "right":
            # 进入文件夹
            cur_item = self.items[self.list_view.index]
            if cur_item["is_dir"]:
                self.current_path /=  cur_item["name"]
                new_content = self._load_dir(self.current_path)
                self.items = new_content["content"]
                self._refresh_list()
            else:
                pass
        elif key == "left":
            self.current_path = Path(self.current_path).parent
            new_content = self._load_dir(self.current_path)
            self.items = new_content["content"]
            self._refresh_list()
        elif key == "enter":
            cur_item = str(self.current_path)
            # 返回选择的对象
            await self.callback(cur_item)

    def _refresh_list(self):
        self.list_view.clear()
        logging.info(f"进入目录{self.current_path}")
        self.cur_path.update(f"当前路径: {str(self.current_path)}")
        if self.items:
            for item in self.items:
                self.list_view.append(ListItem(Label(self._format_name(item))))
            self.list_view.index = 0
        else:
            self.list_view.append(ListItem(Label("当前目录为空")))
        return

    def _load_dir(self, path):
        """这里模拟获取文件夹内容，实际应请求接口"""
        self.current_path = path
        return self.opapi.get_cloud_dir_info(path, password="", page=1, per_page=8, refresh=True)

class FileSelectorApp(App):
    """主TUI应用"""
    CSS_PATH = "style.tcss"
    BINDINGS = []
    AUTO_FOCUS = ""

    def __init__(self, main_logic):
        super().__init__()
        self.main_logic = main_logic

    def compose(self) -> ComposeResult:
        yield Vertical(id="top_area")  # 动态区
        yield RichLog(id="log_area", highlight=False, auto_scroll=True, markup=True)

    async def on_mount(self) -> None:
        # 启动时显示欢迎页
        await self.show_welcome()
        # 启动逻辑
        asyncio.create_task(self.main_logic())

    async def show_welcome(self):
        await self.clear_top()
        top_area = self.query_one("#top_area", Vertical)
        await top_area.mount(WelcomeScreen())

    async def show_input(self, prompt: str, callback, default_value, placeholder: str):
        """在覆盖层(layer)显示一个输入弹窗"""
        await self.clear_top()
        await self.mount(InputDialog(prompt, callback, default_value, placeholder, id="input_dialog"))

    async def show_file_browser(self, opapi: oplist_api.OpenListAPI, content_dict, callback):
        """显示文件浏览器"""
        await self.clear_top()
        top_area = self.query_one("#top_area", Vertical)
        file_browser = FileBrowser(opapi, content_dict, callback, id="file_browser")
        await top_area.mount(file_browser)

    async def clear_top(self):
        """清空顶部区域"""
        top_area = self.query_one("#top_area", Vertical)
        await top_area.remove_children()

    def on_log_message(self, message: LogMessage) -> None:
        """渲染日志消息"""
        log_area = self.query_one("#log_area", RichLog)
        colors = {
            logging.DEBUG: "cyan",
            logging.INFO: "green",
            logging.WARNING: "yellow",
            logging.ERROR: "red",
            logging.CRITICAL: "magenta bold",
        }
        style = colors.get(message.level, "white")
        log_area.write(f"[{style}]{message.text}")