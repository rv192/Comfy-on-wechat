import sys
from loguru import logger


def init_logger_config(level="INFO", keep_stderr=False, keep_file=False):
    """初始化日志配置

    :level: 最小日志级别
    :keep_stderr: 是否保留输出控制台
    :keep_file: 是否保留输出文件
    """

    # if not keep_stderr:
    #     logger.remove()

    logger.remove()
    if keep_stderr:
        logger.add(sys.stderr, level=level)

    if keep_file:
        logger.add("./logs/{time:YYYY-MM-DD}.log", level=level.upper(),
                    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
                    rotation="20 MB", retention="10 days")
        print("文件日志配置完成")
