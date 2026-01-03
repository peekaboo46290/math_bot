from pydantic import BaseModel
from typing import Any
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    #filename='neo4j_debug.log',
    filename='site_debug.log',
    filemode='w'
)#change for each task

logger = logging.getLogger(__name__)
