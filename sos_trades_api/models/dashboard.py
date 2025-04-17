import abc
from enum import Enum
from typing import Optional, List


class DashboardAttributes(str, Enum):
    STUDY_CASE_ID = 'study_case_id'
    ID = 'id'
    ITEMS = 'items'


class DisplayableItemType(str, Enum):
    TEXT = 'text'
    GRAPH = 'graph'
    SECTION = 'section'


class Position:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y


class Size:
    def __init__(self, cols: int, rows: int):
        self.cols = cols
        self.rows = rows


class DisplayableItem(abc.ABC):
    def __init__(
            self,
            item_type: DisplayableItemType,
            position: Optional[Position] = None,
            size: Optional[Size] = None,
            data: Optional[dict] = None,
    ):
        self.item_type = item_type
        self.position = position
        self.size = size
        self.data = data or {}
        self.id = id

    @abc.abstractmethod
    def serialize(self) -> dict:
        pass


class DashboardText(DisplayableItem):
    def __init__(self, content: str, position: Position, size: Size):
        super().__init__(
            item_type=DisplayableItemType.TEXT,
            position=position,
            size=size,
            data={"content": content}
        )

    def serialize(self):
        return {
            "item_type": self.item_type,
            "position": self.position,
            "size": self.size,
            "data": self.data,
            "id": self.id,
        }


class DashboardGraph(DisplayableItem):
    def __init__(self, discipline_name: str, name: str, plot_index: int, graph_data: dict, position: Position,
                 size: Size):
        self.discipline_name = discipline_name
        self.name = name
        self.plot_index = plot_index
        super().__init__(
            item_type=DisplayableItemType.GRAPH,
            position=position,
            size=size,
            data={"graphData": graph_data}
        )

    def serialize(self):
        return {
            "discipline_name": self.discipline_name,
            "name": self.name,
            "plot_index": self.plot_index,
            "data": self.data,
            "item_type": self.item_type,
            "position": self.position,
            "size": self.size,
        }

    @property
    def identifier(self) -> str:
        return f"{self.discipline_name}-{self.name}-{self.plot_index}"


class DashboardSection(DisplayableItem):
    def __init__(self, title: str, position: Position, size: Size, children: List[DisplayableItem]):
        super().__init__(
            item_type=DisplayableItemType.SECTION,
            position=position,
            size=size,
            data={"title": title, "children": children}
        )

    def serialize(self):
        return {
            "item_type": self.item_type,
            "position": self.position,
            "size": self.size,
            "id": self.id,
            "data": self.data,
        }


class Dashboard:
    def __init__(self, study_case_id: int, items: List[DisplayableItem]):
        self.study_id = study_case_id
        self.items = items

    def serialize(self):
        return {
            "study_case_id": self.study_id,
            "items": [item.serialize() for item in self.items],
        }
