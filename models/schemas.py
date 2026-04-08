from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class FileTreeSelectionModel(BaseModel):
    root_path: str
    root_name: str
    selections: Dict[str, Dict[str, Any]]

class FileTreeProfileModel(BaseModel):
    name: str
    root_path: str
    selections: Dict[str, Dict[str, Any]]

class InjectArtifactModel(BaseModel):
    artifact: str

class PresetModel(BaseModel):
    preset_id: str
    config: Dict[str, Any]

class ActiveConfigModel(BaseModel):
    config: Dict[str, Any]

class ChatRequest(BaseModel):
    message: str

class JobDefinitionModel(BaseModel):
    name: str
    instructions: str
    trigger: str
    scripts: List[str] = []

class JobScheduleModel(BaseModel):
    id: Optional[str] = None
    job_name: str
    scheduled_datetime_iso: str
    priority: int = 100
    args: Optional[Dict[str, Any]] = None

class CycleModel(BaseModel):
    name: str
    triggers: List[Any]

class ModelFetchRequest(BaseModel):
    url: str
    filename: Optional[str] = None
    expected_sha256: Optional[str] = None

class SnapshotSaveModel(BaseModel):
    filename: str
    components: List[Dict[str, Any]]

class SnapshotLoadModel(BaseModel):
    filename: str
