# text_video/providers/google_operation_stub.py

from google.genai.types import GenerateVideosOperation


def make_operation_stub(operation_name: str) -> GenerateVideosOperation:
    """
    从 operation_name 反序列化一个最小合法的 GenerateVideosOperation。
    只提供 name，其余字段由 client.operations.get 填充。
    """
    return GenerateVideosOperation(
        name=operation_name,
        done=None,
        error=None,
        result=None,
        response=None,
        metadata=None,
    )
