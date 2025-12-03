from .method import TextVideo  # 便于外部 from ... import TextVideo
# Import schema to ensure it registers with SchemaRegistry
from . import schema  # noqa: F401
