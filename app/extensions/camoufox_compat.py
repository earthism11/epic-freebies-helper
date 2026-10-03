# -*- coding: utf-8 -*-
"""Camoufox 配置兼容补丁。

browserforge 的指纹数据是运行时从上游 master 拉取的（数据文件超过 5 周自动更新），
新数据可能生成当前 Camoufox 浏览器构建 properties.json 未收录的属性
（例如 navigator.appCodeName），camoufox.utils.validate_config 默认会直接抛
UnknownProperty 终止整个领取任务。

这里把校验逻辑改为：忽略未收录的属性并记录日志，其余属性仍走原有严格校验。
被忽略的属性只是不做伪装注入（如 appCodeName 在所有 Firefox 上恒为 "Mozilla"），
对指纹一致性影响可忽略，但可以避免任务硬失败。
"""
from __future__ import annotations

from loguru import logger

_PATCH_FLAG = "_epic_compat_applied"


def install_camoufox_config_compat() -> None:
    try:
        import camoufox.utils as camoufox_utils
    except Exception as err:  # pragma: no cover - camoufox 未安装时无需打补丁
        logger.debug("Camoufox compat patch skipped | reason={} | {}", type(err).__name__, err)
        return

    if getattr(camoufox_utils, _PATCH_FLAG, False):
        return

    original_validate = camoufox_utils.validate_config

    def validate_config(config_map, path=None):
        try:
            property_types = camoufox_utils._load_properties(path=path)
        except Exception:
            # 属性表都读不到时，退回原始行为，避免掩盖真正的安装问题
            original_validate(config_map, path=path)
            return

        known = {key for key in property_types}
        unknown = [key for key in config_map if key not in known]
        if unknown:
            for key in unknown:
                logger.warning(
                    "Camoufox compat | drop unknown config property: {} "
                    "(browserforge data newer than camoufox build)", key
                )
            config_map = {key: value for key, value in config_map.items() if key in known}

        original_validate(config_map, path=path)

    camoufox_utils.validate_config = validate_config
    setattr(camoufox_utils, _PATCH_FLAG, True)
    logger.info("Camoufox compat patch applied | strict_unknown_property=False")
