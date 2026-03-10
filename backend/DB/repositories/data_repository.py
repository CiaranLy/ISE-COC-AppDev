"""Data repository."""

from DB.models.data import Data
from DB.repositories.base import AsyncRepository


class DataRepository(AsyncRepository[Data]):
    model_cls = Data
