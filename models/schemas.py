from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class PresetModel(BaseModel):
    preset_id: str
    config: Dict[str, Any]

class ActiveConfigModel(BaseModel):
    config: Dict[str, Any]

class ModelFetchRequest(BaseModel):
    url: str
    filename: Optional[str] = None
    expected_sha256: Optional[str] = None

class SnapshotSaveModel(BaseModel):
    filename: str
    components: List[Dict[str, Any]]

class SnapshotLoadModel(BaseModel):
    filename: str

class TestBenchmarkRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = None

class DeltaBlockItem(BaseModel):
    id: str
    order: Optional[int] = None
    enabled: Optional[bool] = True
    name: Optional[str] = None
    file: Optional[str] = None
    begin_bracket: Optional[str] = None
    end_bracket: Optional[str] = None
    description: Optional[str] = None

class DeltaUpdateRequest(BaseModel):
    block_id: Optional[str] = None
    file: Optional[str] = None
    content: str
    recompile: Optional[bool] = True

