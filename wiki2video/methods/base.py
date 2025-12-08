import abc
import json
import os.path

from wiki2video.dao.working_block_dao import WorkingBlockDAO
from wiki2video.core.working_block import WorkingBlock, WorkingBlockStatus
from wiki2video.schema.action_spec import ActionSpec
from wiki2video.schema.generation_result_schema import GenerationResult


def check_previous_done(previous_id: str) -> WorkingBlockStatus:
    dao = WorkingBlockDAO()
    block = dao.get_by_id(previous_id)

    # 1. 上一个 block 不存在 → DAG 损坏
    if block is None:
        return WorkingBlockStatus.ERROR
    # 2. 上一个 block 明确失败
    if block.status == WorkingBlockStatus.ERROR:
        return WorkingBlockStatus.ERROR
    # 3. JSON 校验
    try:
        result = json.loads(block.result_json or "{}")
    except Exception:
        return WorkingBlockStatus.ERROR
    output_path = result.get("output_path")
    # 4. 若状态成功但文件不存在 → 视为 PENDING（重新生成）
    if block.status == WorkingBlockStatus.SUCCESS:
        if output_path and os.path.exists(output_path):
            return WorkingBlockStatus.SUCCESS
        else:
            return WorkingBlockStatus.PENDING
    # 5. 若状态 Pending / Running
    return block.status



class BaseMethod(abc.ABC):
    NAME: str = "Base"        # Override

    def __init__(self) -> None:
        super().__init__()

    @abc.abstractmethod
    def run(self, spec: ActionSpec) -> WorkingBlock:
        """
        Create a new WorkingBlock for this action.
        Does NOT execute heavy work - just creates and saves the block.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def poll(self, wb: WorkingBlock) -> GenerationResult:
        """
        Do actual work; may run multiple times (async) or finish in one call (sync).
        Must update wb.status, wb.output_path, wb.result_json.
        """
        raise NotImplementedError

