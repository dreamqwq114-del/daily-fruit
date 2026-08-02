"""FastAPI Cloud 的仓库根目录入口。

FastAPI Cloud 的 monorepo 运行器可能从仓库根目录启动；实际应用仍位于
``backend/app/main.py``。这里仅把 ``backend`` 加入模块搜索路径并转发
同一个 FastAPI ``app`` 对象，不复制任何业务逻辑。
"""

from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402  (路径准备后再导入应用)

__all__ = ["app"]
