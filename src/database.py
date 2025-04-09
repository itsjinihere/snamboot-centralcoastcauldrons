from src import config
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import declarative_base

connection_url = config.get_settings().POSTGRES_URI
engine = create_engine(connection_url, pool_pre_ping=True)

metadata = MetaData()
Base = declarative_base(metadata=metadata)
