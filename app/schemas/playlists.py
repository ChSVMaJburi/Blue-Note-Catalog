from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.catalog import CatalogInput, Name


class PlaylistInput(CatalogInput):
    name: Name


class PlaylistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
