from pydantic import BaseModel


class DataSourceCreate(BaseModel):
    name: str
    source_type: str
    base_url: str | None = None
    api_key_env_var: str | None = None
    config_json: str | None = None


class DataSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    base_url: str | None
    api_key_env_var: str | None
    config_json: str | None

    model_config = {"from_attributes": True}
