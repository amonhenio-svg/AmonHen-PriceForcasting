from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    source_type = Column(String, nullable=False)  # entsoe, open_meteo, commodity
    base_url = Column(String, nullable=True)
    api_key_env_var = Column(String, nullable=True)  # env var name holding the API key
    config_json = Column(Text, nullable=True)  # extra config as JSON string
